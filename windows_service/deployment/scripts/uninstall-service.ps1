param(
    [string]$ServiceName = "QR-MCP"
)

$ErrorActionPreference = "Stop"

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $service) {
    Write-Host "Dienst $ServiceName ist nicht installiert"
    return
}

if ($service.Status -ne 'Stopped') {
    Write-Host "Stoppe Dienst $ServiceName"
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    $service.WaitForStatus('Stopped', (New-TimeSpan -Seconds 30)) | Out-Null
}

Write-Host "Entferne Dienst $ServiceName"
sc.exe delete $ServiceName | Out-Null
