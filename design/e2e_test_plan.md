# End-to-End-Testplan MCP-Agent

## Zielsetzung

Nachweis, dass MCP-Client, Windows-Agent und Python-Dispatcher eine durchgängige Befehlskette inklusive Fehlerszenarien verarbeiten können.

## Testmatrix

| Szenario | Beschreibung | Erwartung |
|----------|--------------|-----------|
| Happy Path | Signierter `browser.open`-Befehl via Named Pipe | Receipt `accepted`, Result `ok`, Audit-Log enthält Laufzeit |
| Dry-Run | `powershell.run` mit `dry_run=true` | Result `dry-run`, keine Prozessausführung |
| Sandbox-Verstoß | PowerShell-Skript enthält `Remove-Item` | Result `rejected`, Audit-Detail `PowerShell-Befehl blockiert` |
| Timeout | Handler schlägt Timeout (simulierter Delay) | Result `timeout`, Wiederanlauf mit Backoff |
| Neustart | Dienst stoppt während Verarbeitung | Befehl verbleibt in `inbox.jsonl`, wird nach Neustart erneut gelesen |
| Lasttest | 500 Commands in 60 s | Durchsatz ≥ 8 msg/s, keine verlorenen Nachrichten |

## Testwerkzeuge

* **Simulation**: Python-Skript (`tests/e2e/test_client_sim.py`, TODO) erzeugt Befehle und verifiziert Acknowledgements.
* **Load Runner**: `locust`-Profil für TCP-Endpunkt (200 parallele Nutzer).
* **Fault Injection**: PowerShell-Skript `tests/e2e/faults.ps1` toggelt Dienststatus.

## Wiederanlaufstrategien

1. Bei `timeout` wird der Befehl mit exponentiellem Backoff (1 s, 2 s, 4 s) erneut gesendet.
2. Falls `invalid-signature`, eskaliere und blockiere Schlüssel (`SignatureValidator.require_signature=true`).
3. Bei Dienst-Neustart: Monitor prüft `inbox.jsonl` und setzt Datei-Lock, um doppelte Verarbeitung zu verhindern.

## Artefakte

* JSONL-Dateien `logs/mcp-results.jsonl`, `logs/mcp-audit.jsonl`
* Windows EventLog Quelle `QR-MCP`
* Zusammenfassung in `reports/e2e-summary.csv` (Delta zu Erwartung in Prozentangaben)
