param(
    [string]$Configuration = "Release",
    [string]$OutputDirectory = "artifacts"
)

$ErrorActionPreference = "Stop"

Write-Host "Building Windows MCP Agent ($Configuration)"

dotnet publish ..\windows_service\McpAgentService.csproj -c $Configuration -o "$OutputDirectory\agent"

# MSI-Erstellung via WiX (sofern installiert)
$wixToolset = ${env:WIX} ?? "C:\\Program Files (x86)\\WiX Toolset v3.11\\bin"
$heat = Join-Path $wixToolset "heat.exe"
$candle = Join-Path $wixToolset "candle.exe"
$light = Join-Path $wixToolset "light.exe"

if (Test-Path $heat) {
    & $heat dir "$OutputDirectory\agent" -dr INSTALLDIR -cg AgentComponents -sreg -srd -out "$OutputDirectory\agent.wxs"
    & $candle "$OutputDirectory\agent.wxs" -out "$OutputDirectory\agent.wixobj"
    & $light "$OutputDirectory\agent.wixobj" -o "$OutputDirectory\qr-mcp-agent.msi"
    Write-Host "MSI erstellt: $OutputDirectory\qr-mcp-agent.msi"
} else {
    Write-Warning "WiX Toolset nicht gefunden – MSI wird übersprungen"
}

# Chocolatey Paket vorbereiten
Copy-Item deployment\chocolatey\* "$OutputDirectory\choco" -Recurse -Force
Copy-Item "$OutputDirectory\agent\*" "$OutputDirectory\choco\tools" -Recurse

Write-Host "Chocolatey-Paketvorlage liegt unter $OutputDirectory\choco"
