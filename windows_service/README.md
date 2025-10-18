# Windows MCP Agent Service

Diese Vorlage implementiert einen Windows-Dienst, der MCP-Nachrichten über drei Transportkanäle entgegennimmt:

1. **Named Pipes** (`\\.\pipe\qr-mcp`)
2. **TCP** (Standard-Port `48123`)
3. **gRPC** (Proto-konformes Interface auf Basis des TCP-Endpunkts)

Alle Kanäle kapseln Nachrichten im `MessageEnvelope`-Format:

```json
{
  "transport": "named-pipe",
  "sequence": 42,
  "command": { ... MCP command payload ... }
}
```

Der Dienst parst die Nutzlast, prüft Signaturen und reicht Befehle an die Python-Implementierung weiter (über JSONL-Queue oder REST-Call). Die C#-Implementierung ist so strukturiert, dass Erweiterungen (z. B. Telemetrie) modular ergänzt werden können.

## Projektstruktur

```
windows_service/
├── README.md
├── McpAgentService.csproj
└── src/
    ├── Program.cs
    ├── AgentWorker.cs
    ├── Ipc/NamedPipeListener.cs
    ├── Ipc/TcpListenerHost.cs
    └── Security/SignatureVerifier.cs
```

## Build & Installation

```powershell
# Build
 dotnet build -c Release windows_service/McpAgentService.csproj

# Install as Windows service
 sc create QR-MCP binPath= "C:\\path\\to\\McpAgentService.exe" start= auto
 sc start QR-MCP
```

Für lokale Tests kann das Projekt auch als Konsolenanwendung gestartet werden (`dotnet run`).

## Transportdetails

### Named Pipes

* Server: `NamedPipeServerStream("qr-mcp", PipeDirection.InOut, maxNumberOfServerInstances: 4)`
* Client authentifiziert sich über Windows-Logon-Token.
* Nachrichtenlänge wird über 4-Byte-Präfix (Little Endian) übertragen.

### TCP

* Listener auf `0.0.0.0:48123`.
* TLS optional via `ServerOptionsSelectionCallback`.
* Heartbeat alle 30 Sekunden (`event`-Nachricht mit `kind="heartbeat"`).

### gRPC

* Proto-Definition im Kommentar (siehe `Ipc/TcpListenerHost.cs`).
* Service stellt `SubmitCommand` und `StreamResults` bereit.

## Sicherheit

* Signaturprüfung via HMAC-SHA256 (`Security/SignatureVerifier.cs`).
* Rollenrechte im JSON `roles.json` (wird beim Start geladen).
* Audit-Log schreibt Windows EventLog + JSONL-Datei (`%PROGRAMDATA%\QR\audit.jsonl`).

## Integration mit Python-Agent

Der Dienst serialisiert bestätigte Befehle in `C:\\ProgramData\\QR\\inbox.jsonl`. Der Python-MCP-Service kann den Pfad als Quelle für `iter_json_instructions()` nutzen. Ergebnisse werden symmetrisch in `outbox.jsonl` geschrieben und bei Bedarf über TCP/gRPC zurückgestreamt.
