# Aktionsadapter & Sandbox-Konzept

## Übersicht

| Aktion                | Handler-Klasse                      | Rollen        | Sandbox                                   | Dry-Run |
|----------------------|-------------------------------------|---------------|-------------------------------------------|---------|
| Logging               | `LoggingHandler`                    | `*`           | Keine (nur Audit)                         | Ja      |
| Browser-Automation    | `BrowserAutomationHandler`          | `automation`, `admin` | Playwright-Context ohne Persistenz, Download-Whitelist | Ja |
| PowerShell            | `PowerShellHandler`                 | `ops`, `admin`| Blockliste (`Remove-Item`, `Format-Drive`), Windows-only | Ja |
| Registry              | `RegistryHandler`                   | `ops`, `admin`| Root-Whitelist (`HKCU`, `HKLM`), Operationen `query`/`set` | Ja |

## Sandbox-Prinzipien

1. **Least Privilege**: Jeder Handler deklariert `allowed_roles`. Zusätzlich erzwingt der `RolePolicy`-Layer globale Beschränkungen.
2. **Dry-Run**: Für risikoarme Vorprüfung. Handler liefern Klartextbeschreibung.
3. **Timeboxing**: `default_timeout` pro Handler verhindert Hänger (Browser 120 s, PowerShell 60 s, Registry 10 s).
4. **Input Validation**: PowerShell blockiert gefährliche Kommandos (konfigurierbar); Registry prüft erlaubte Roots.

## Erweiterungspunkte

* Weitere Adapter (z. B. WMI, gRPC) implementieren `ActionHandler` und können Sandbox via `SandboxViolation` signalisieren.
* Rollenmatrix erweiterbar über `RolePolicy.from_mapping()` im Service.
* Für Playwright kann optional ein Download-Verzeichnis injiziert werden, um Dateizugriffe zu isolieren.
