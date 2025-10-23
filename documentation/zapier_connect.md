# Zapier-Integration über das QR-Gateway

Dieser Leitfaden beschreibt, wie ein bestehendes Zapier-Webhooks-Szenario mit dem Gateway der QR-Automationsplattform verbunden wird. Voraussetzung ist ein eingerichteter Catch-Hook in Zapier ("Catch Hook"-Trigger innerhalb eines Zaps) sowie ein lokal installiertes Projekt-Environment (`pip install -e .[dev]`).

## 1. Zapier-Webhook vorbereiten
1. Öffne den gewünschten Zap in Zapier und füge als ersten Schritt den Trigger **Webhooks by Zapier → Catch Hook** hinzu.
2. Kopiere die generierte **Custom Webhook URL**. Sie besitzt das Muster `https://hooks.zapier.com/hooks/catch/<app_id>/<trigger_id>/`.
3. Teste den Zapier-Hook direkt in Zapier, um sicherzustellen, dass er Anfragen entgegennehmen kann.

## 2. Gateway-Konfiguration anpassen
Lege eine eigene Konfigurationsdatei, z. B. `configs/zapier-gateway.yaml`, mit folgendem Inhalt an (Webhook-URL ersetzen):

```yaml
queue_size: 8
concurrency: 1
adapters:
  - name: zapier-webhook
    implementation: qr_automation.gateway.adapters.zapier:ZapierAdapter
    protocols: [REST, Zapier]
    options:
      webhook_url: https://hooks.zapier.com/hooks/catch/1234567/abcdef/
      timeout: 30
```

> Tipp: Für produktive Installationen kann die URL als Umgebungsvariable verwaltet und beim Start in die YAML-Datei geschrieben werden.

## 3. Verbindung mit der CLI testen
Die CLI besitzt den neuen Befehl `gateway send`, der eine einzelne Nachricht durch den konfigurierten Adapter leitet. Beispielaufruf:

```bash
python -m qr_automation.cli gateway send \
  --config configs/zapier-gateway.yaml \
  --adapter zapier-webhook \
  --message "Testdurchlauf aus dem QR-Gateway" \
  --room labor \
  --sender-id blue \
  --sender-type human \
  --metadata '{"origin": "integration-test"}'
```

Nach erfolgreichem Aufruf erscheinen zwei Ausgaben:

1. Bestätigung, dass die Nachricht gesendet wurde.
2. Die JSON-Antwort von Zapier (oder ein Platzhalter, falls Zapier keinen Inhalt zurückliefert).

## 4. Fehlerbehandlung
* Bei ungültigem JSON im `--metadata`-Flag bricht der Befehl mit einer verständlichen Fehlermeldung ab.
* Liefert Zapier einen Fehlerstatus (≥ 400), wird der Prozess mit Exit-Code 1 beendet, und die Fehlermeldung von Zapier erscheint in der Konsole.
* Nach jedem Aufruf wird der Gateway-Dienst sauber gestoppt, sodass keine Hintergrund-Tasks offen bleiben.

## 5. Weiterführende Nutzung
* Die Konfiguration kann mehrere Adapter parallel enthalten. `--adapter` bestimmt, welcher Adapter den Dispatch übernimmt.
* Die gesendete Nachricht steht auch in den Audit-Logs des Chat-Servers zur Verfügung, falls der Server mit derselben Datenbank betrieben wird.
* Für automatisierte Workflows kann der CLI-Befehl in Skripte oder GitHub-Actions integriert werden.
