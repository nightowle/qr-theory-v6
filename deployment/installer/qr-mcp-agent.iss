#define MyAppName "QR MCP Agent Service"
#define MyAppPublisher "QR Automation"
#define MyAppVersion "__APP_VERSION__"
#define MyPublishDir "__PUBLISH_DIR__"
#define MyOutputDir "__OUTPUT_DIR__"

[Setup]
AppId={{F0B29EB3-A17F-4DF0-8A1B-EAF938789A28}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\QR Automation\MCP Agent
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=qr-mcp-agent-setup
OutputDir={#MyOutputDir}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\McpAgentService.exe
WizardStyle=modern

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MyPublishDir}\\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File \"{app}\\deployment\\scripts\\install-service.ps1\" -ServiceName \"QR-MCP\" -DisplayName \"QR MCP Agent\" -Description \"QR Automation MCP Agent service\""; Flags: runhidden waituntilterminated; StatusMsg: "Registriere Windows-Dienst..."

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File \"{app}\\deployment\\scripts\\uninstall-service.ps1\" -ServiceName \"QR-MCP\""; Flags: runhidden waituntilterminated; RunOnceId: "QR-MCP-Uninstall-Service"; StatusMsg: "Entferne Windows-Dienst..."

[Icons]
Name: "{group}\\Dienst-Dokumentation"; Filename: "{app}\\README.txt"; Check: FileExists(ExpandConstant('{app}\\README.txt'))
Name: "{group}\\Dienst-Logs"; Filename: "%SystemRoot%\\System32\\notepad.exe"; Parameters: "\"%ProgramData%\\QR\\audit.jsonl\""
