# Maschinen-Kommunikations-Protokoll (MCP) – Referenzspezifikation

## 1. Überblick

Das MCP beschreibt einen minimierten Austauschkanal zwischen einem Steuer-Client (z. B. QR-Gateway) und einem ausführenden Dienst (z. B. Windows-Agent). Jede Kommunikation erfolgt über streng typisierte JSON-Nachrichten, die kryptographisch signiert und mit Rollenrechten versehen sind. Ziel ist ein konsistentes Audit über die komplette Befehlskette.

## 2. Nachrichtenklassen

| Typ                | Beschreibung                                                                    | Schlüsselattribute                            |
|--------------------|----------------------------------------------------------------------------------|-----------------------------------------------|
| `command`          | Ausführungsanweisung mit Zielaktion und Payload                                  | `id`, `action`, `payload`, `role`, `signature`|
| `event`            | Status-/Heartbeat-Information aus dem Agent                                     | `id`, `kind`, `payload`, `occurred_at`        |
| `receipt`          | Quittung über den Eingang eines Befehls                                         | `instruction_id`, `received_at`, `status`     |
| `result`           | Ergebnis eines Befehls nach Ausführung                                          | `instruction_id`, `status`, `detail`          |

Alle Nachrichten besitzen ISO-8601-Zeitstempel in UTC und optional eine `correlation_id`, um Ketten zwischen Command, Receipt, Result und Folgeereignissen zu bilden.

## 3. Datenmodell der Befehlsnachricht

```json
{
  "id": "uuid",
  "action": "browser.open",
  "payload": {"url": "https://example.org"},
  "issued_at": "2024-04-01T12:00:00Z",
  "role": "automation",
  "dry_run": false,
  "timeout": 120.0,
  "metadata": {
    "priority": "standard",
    "trace": "qr-gateway:42"
  },
  "signature": {
    "algorithm": "hs256",
    "key_id": "agent-shared",
    "value": "0123abcd..."
  }
}
```

Der zu signierende Inhalt wird kanonisch serialisiert (JSON mit `sort_keys=True`, `separators=(",", ":")`). Nur die Felder aus `canonical_dict()` werden berücksichtigt, damit mehrere Implementierungen dieselbe Bytefolge erzeugen.

## 4. Quittungen & Ergebnisse

* **CommandReceipt** (`command_receipt`): Wird unmittelbar nach Annahme auf dem Agent erstellt. Pflichtfelder: `instruction_id`, `received_at`, `status` (`accepted`/`rejected`), optionale `detail`-Map (z. B. Rolle, Transportkanal).
* **InstructionResult** (`command_result`): Wird nach Abschluss der Aktion erstellt. Pflichtfelder: `status` (`ok`, `failed`, `timeout`, `rejected`, `dry-run`, `invalid-signature`, `forbidden`, `unhandled`), `detail` (freier Text oder strukturierter JSON-String), `produced_at`, optionale `duration_ms`, `audit_reference`.

## 5. Signaturverfahren

* Algorithmus: HMAC-SHA256 (`hs256`).
* `key_id`: verweist auf einen geheimen Schlüssel des Agents (z. B. `agent-primary`).
* Validierung: `SignatureValidator.verify()` muss einen bekannten Schlüssel liefern und `InstructionSignature.verify()` erfolgreich abschließen. Fehlerzustände:
  * `invalid-signature`: Signaturprüfung fehlgeschlagen.
  * `signature-missing`: Signatur erforderlich, aber nicht vorhanden.
  * `unknown-key`: Schlüssel unbekannt (Audit-Detail enthält `key_id`).

## 6. Rollen & Berechtigungen

Rollen definieren erlaubte Aktionspräfixe. Beispielkonfiguration:

```toml
[roles]
admin = ["*"]
automation = ["browser.open", "log"]
ops = ["powershell.run", "system.registry"]
observer = ["log"]
```

Der Dienst prüft sowohl die globale Rollenrichtlinie (`RolePolicy`) als auch die handler-spezifische Whitelist. Die erste Verletzung führt zum Result-Status `forbidden` und einem Audit-Eintrag.

## 7. Sandboxing & Dry-Run

* **Dry-Run**: Kann pro Nachricht (`dry_run=true`) oder global im Dienst aktiviert werden. Handler müssen eine sprechende Beschreibung liefern (`ActionHandler.describe_dry_run`).
* **Sandbox**: Handler dürfen `SandboxViolation` auslösen (z. B. PowerShell-Blockliste, Registry-Root-Beschränkung). Der Dienst antwortet mit `rejected` und zeichnet den Verstoß im Audit auf.

## 8. Zeitouts & Wiederholungen

* Pro Nachricht optionales `timeout` (Sekunden, float). Fallback: Handler-Default oder Dienst-Default.
* Zeitüberschreitung resultiert in `timeout` und triggert Wiederanlaufstrategie (siehe End-to-End-Testplan).

## 9. Audit-Log

Jeder Befehlszyklus erzeugt einen JSONL-Datensatz (`mcp-audit.jsonl`) mit Feldern:

* `instruction_id`, `action`, `role`, `issued_at`, `started_at`, `completed_at`
* `status`, `detail`
* `dry_run`, `signature_valid`
* `receipt.status`, `receipt.received_at`, `receipt.detail`

Die Kombination ermöglicht Rückverfolgbarkeit über alle Transportstufen.

## 10. Transport-neutraler Rahmen

Die Spezifikation macht keine Annahmen über den Transport. Empfohlen wird eine Kapselung in `MessageEnvelope`-Pakete mit Headern (`transport`, `sequence`, `compression`). Beispiele finden sich in `windows_service/README.md`.
