param(
    [string]$ServiceName = "QR-MCP",
    [string]$DisplayName = "QR MCP Agent",
    [string]$BinaryPath = "",
    [string]$Description = "QR Automation MCP Agent service"
)

$ErrorActionPreference = "Stop"

if (-not $BinaryPath) {
    $BinaryPath = Join-Path $PSScriptRoot "..\McpAgentService.exe"
}

$resolvedBinary = [System.IO.Path]::GetFullPath($BinaryPath)

if (-not (Test-Path $resolvedBinary)) {
    throw "Dienst-Binärdatei wurde nicht gefunden: $resolvedBinary"
}

function Stop-ServiceIfExists {
    param([string]$Name)
    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        if ($existing.Status -ne 'Stopped') {
            Write-Host "Stoppe existierenden Dienst $Name"
            Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
            $existing.WaitForStatus('Stopped', (New-TimeSpan -Seconds 30)) | Out-Null
        }
        Write-Host "Entferne existierenden Dienst $Name"
        sc.exe delete $Name | Out-Null
        Start-Sleep -Seconds 2
    }
}

Stop-ServiceIfExists -Name $ServiceName

Write-Host "Registriere Dienst $ServiceName"
New-Service -Name $ServiceName -BinaryPathName $resolvedBinary -DisplayName $DisplayName -StartupType Automatic | Out-Null

if ($Description) {
    sc.exe description $ServiceName "$Description" | Out-Null
}

Write-Host "Starte Dienst $ServiceName"
Start-Service -Name $ServiceName | Out-Null
