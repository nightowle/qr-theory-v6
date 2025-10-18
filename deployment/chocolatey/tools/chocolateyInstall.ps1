$ErrorActionPreference = 'Stop'

$toolsDir   = Split-Path -parent $MyInvocation.MyCommand.Definition
$serviceExe = Join-Path $toolsDir 'McpAgentService.exe'

Install-ChocolateyInstallPackage `
    -PackageName 'qr-automation-mcp' `
    -FileType 'EXE' `
    -SilentArgs "/install" `
    -File $serviceExe

Start-ChocolateyProcessAsAdmin "sc create QR-MCP binPath= '$(Resolve-Path $serviceExe)' start= auto"
Start-ChocolateyProcessAsAdmin "sc start QR-MCP"
