param(
    [string]$Configuration = "Release",
    [string]$OutputDirectory = "artifacts"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$resolvedOutput = (Resolve-Path $OutputDirectory).Path
$publishDir = Join-Path $resolvedOutput "agent"
New-Item -ItemType Directory -Path $publishDir -Force | Out-Null

Write-Host "Building Windows MCP Agent ($Configuration)"

dotnet publish ..\windows_service\McpAgentService.csproj -c $Configuration -o $publishDir

# Zusatzdateien (PowerShell-Skripte, README)
$supportSource = Join-Path $scriptRoot "..\windows_service\deployment"
$deploymentTarget = Join-Path $publishDir "deployment"
if (Test-Path (Join-Path $supportSource "scripts")) {
    New-Item -ItemType Directory -Path $deploymentTarget -Force | Out-Null
    Copy-Item (Join-Path $supportSource "scripts") $deploymentTarget -Recurse -Force
}

$readmeSource = Join-Path $scriptRoot "..\windows_service\README.md"
if (Test-Path $readmeSource) {
    Copy-Item $readmeSource (Join-Path $publishDir "README.txt") -Force
}

$binaryPath = Join-Path $publishDir "McpAgentService.exe"
$version = "1.0.0.0"
if (Test-Path $binaryPath) {
    $version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($binaryPath).FileVersion
}

# MSI-Erstellung via WiX (sofern installiert)
$wixToolset = ${env:WIX} ?? "C:\\Program Files (x86)\\WiX Toolset v3.11\\bin"
$heat = Join-Path $wixToolset "heat.exe"
$candle = Join-Path $wixToolset "candle.exe"
$light = Join-Path $wixToolset "light.exe"

if (Test-Path $heat) {
    & $heat dir $publishDir -dr INSTALLDIR -cg AgentComponents -sreg -srd -out (Join-Path $resolvedOutput "agent.wxs")
    & $candle (Join-Path $resolvedOutput "agent.wxs") -out (Join-Path $resolvedOutput "agent.wixobj")
    & $light (Join-Path $resolvedOutput "agent.wixobj") -o (Join-Path $resolvedOutput "qr-mcp-agent.msi")
    Write-Host "MSI erstellt: $(Join-Path $resolvedOutput 'qr-mcp-agent.msi')"
} else {
    Write-Warning "WiX Toolset nicht gefunden – MSI wird übersprungen"
}

# Chocolatey Paket vorbereiten
$chocoTarget = Join-Path $resolvedOutput "choco"
Copy-Item deployment\chocolatey\* $chocoTarget -Recurse -Force
Copy-Item "$publishDir\*" (Join-Path $chocoTarget "tools") -Recurse

Write-Host "Chocolatey-Paketvorlage liegt unter $chocoTarget"

# Setup.exe über Inno Setup erstellen (falls verfügbar)
$iscc = ${env:INNOSETUP} ?? "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
$installerTemplate = Join-Path $scriptRoot "installer\qr-mcp-agent.iss"
if (Test-Path $iscc -and (Test-Path $installerTemplate)) {
    $installerWorkDir = Join-Path (Resolve-Path $OutputDirectory) "installer"
    New-Item $installerWorkDir -ItemType Directory -Force | Out-Null

    $publishEscaped = $publishDir -replace '\\', '\\\\'
    $outputEscaped = $installerWorkDir -replace '\\', '\\\\'

    $issContent = Get-Content $installerTemplate | ForEach-Object {
        $_ -replace "__PUBLISH_DIR__", $publishEscaped -replace "__OUTPUT_DIR__", $outputEscaped -replace "__APP_VERSION__", $version
    }

    $installerScript = Join-Path $installerWorkDir "qr-mcp-agent.generated.iss"
    Set-Content -Path $installerScript -Value $issContent -Encoding UTF8

    & $iscc $installerScript /Qp

    $expectedSetup = Join-Path $installerWorkDir "qr-mcp-agent-setup.exe"
    if (Test-Path $expectedSetup) {
        Write-Host "Setup erstellt: $expectedSetup"
    } else {
        Write-Warning "Inno Setup wurde ausgeführt, aber die Setup-Datei fehlt. Prüfen Sie das Log."
    }
} else {
    Write-Warning "Inno Setup (ISCC.exe) nicht gefunden – Setup.exe wird übersprungen"
}
