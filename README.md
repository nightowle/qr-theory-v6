![LaTeX build](https://github.com/nightowle/qr-theory-v6/actions/workflows/latex.yml/badge.svg)

# QR Theory v6.00 - Complete Synthesis of Quantum Mechanics and General Relativity

```
[![B uild vN€Ã¤d](https://github.com/nightowle/qr-theory-v6/actions/workflows/build-v6d.yml/badge.svg)](https://github.com/nightowle/qr-theory-v6/actions/workflows/build-v6d.yml)
[![Release vN€Ã¤d](https://img.shields.io/github/v/release/nightowle/qr-theory-v6.json.svg)](https://github.com/nightowle/qr-theory-v6/releases)
```

## Lokale Automationsplattform

Dieses Repository enthält nun eine erste Referenzimplementierung für die im Projektauftrag genannten Automationsziele:

* `qr_automation.chat`: FastAPI-basierte Chatraum-Instanz mit Audit-Log (SQLite/JSONL) und WebSocket-Broadcasting.
* `qr_automation.gateway`: Adapter-Gateway mit Warteschlange, Rate-Limiting, Caching und Hot-Swap-Konfiguration für verschiedene KI-Systeme (inklusive Echo-, OpenAI- und Llama.cpp-Adapter).
* `qr_automation.mcp`: MCP-Dienst mit Befehlsschlange und Dispatcher für Browser-, PowerShell- und Logging-Aktionen.
* `qr_automation.cli`: Einstiegspunkt, um Chat-Server (`chat`) oder MCP-Dienst (`mcp`) lokal zu starten.

Zum schnellen Testen empfiehlt sich ein virtuelles Environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn qr_automation.chat.server:build_app --factory --host 127.0.0.1 --port 8000
```

Die Gateway-Konfiguration kann über YAML/JSON-Dateien gesteuert werden. Eine Beispielkonfiguration liegt unter `documentation/gateway-config.sample.yaml`. Verwaltung erfolgt über die CLI:

```bash
python -m qr_automation.cli gateway validate --config documentation/gateway-config.sample.yaml
python -m qr_automation.cli gateway list --config documentation/gateway-config.sample.yaml
```

Die Test-Suite deckt Persistenz, API-Fluss, Gateway-Dispatch und MCP-Ergebnisprotokollierung ab:

```bash
pytest
```
