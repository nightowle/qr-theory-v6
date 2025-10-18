$ErrorActionPreference = 'Stop'

Start-ChocolateyProcessAsAdmin 'sc stop QR-MCP'
Start-ChocolateyProcessAsAdmin 'sc delete QR-MCP'
