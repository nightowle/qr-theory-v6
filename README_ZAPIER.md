# Zapier Integration for QR v6

## Kanäle
- Slack Channel: #qr-theory
- Rollen-Tags: [Frank] [AI1] [AI2] [AI3] [AI4]

## Zap-Blueprint
1) Trigger: Slack new message in #qr-theory (filter startsWith '[')
   - Action: Webhook POST → role-router /ingest
2) Trigger: Webhook catch from Router
   - Actions: GitHub update /ops/github/project_status.json, append /docs/LOG.md, Slack Ack
3) Trigger: GitHub commit on ai4-build
   - Action: Overleaf Build, Slack Ergebnis verlinken

## ENV
Siehe ops/router/.env.example
