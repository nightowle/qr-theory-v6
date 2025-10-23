from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

import uvicorn

from .chat.models import ChatMessage
from .chat.server import build_app
from .chat.storage import utcnow
from .gateway.config import load_gateway_config
from .gateway.manager import GatewayManager, create_default_gateway
from .gateway.service import GatewayService
from .mcp.service import MCPService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QR Automation Platform Launcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Startet den Chat-Server")
    chat_parser.add_argument("--db", default="./data/chat.db", help="Pfad zur SQLite-Datenbank")
    chat_parser.add_argument("--log", default="./logs/audit.jsonl", help="Audit-Log-Datei")
    chat_parser.add_argument("--host", default="127.0.0.1")
    chat_parser.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("mcp", help="Startet den MCP-Dienst")

    gateway_parser = subparsers.add_parser("gateway", help="Administriert die Gateway-Konfiguration")
    gateway_sub = gateway_parser.add_subparsers(dest="gateway_command", required=True)

    validate_parser = gateway_sub.add_parser("validate", help="Validiert eine Konfigurationsdatei")
    validate_parser.add_argument("--config", required=True, help="Pfad zur Gateway-Konfiguration")

    list_parser = gateway_sub.add_parser("list", help="Listet Adapter aus der Konfiguration auf")
    list_parser.add_argument("--config", required=True, help="Pfad zur Gateway-Konfiguration")

    metrics_parser = gateway_sub.add_parser("metrics", help="Zeigt aktuelle Metriken")
    metrics_parser.add_argument("--config", required=True, help="Pfad zur Gateway-Konfiguration")

    send_parser = gateway_sub.add_parser(
        "send",
        help="Sendet eine Testnachricht über einen konfigurierten Adapter (z. B. Zapier)",
    )
    send_parser.add_argument("--config", required=True, help="Pfad zur Gateway-Konfiguration")
    send_parser.add_argument("--adapter", required=True, help="Name des Zieladapters")
    send_parser.add_argument("--message", required=True, help="Nachrichtentext")
    send_parser.add_argument("--room", default="lab", help="Chat-Raumkennung (Default: lab)")
    send_parser.add_argument(
        "--sender-id",
        default="cli",
        help="Absenderkennung für das Audit-Protokoll (Default: cli)",
    )
    send_parser.add_argument(
        "--sender-type",
        default="system",
        help="Absendertyp, z. B. human, system oder automation",
    )
    send_parser.add_argument(
        "--metadata",
        default="{}",
        help="Optionale Zusatzinformationen als JSON-Dictionary",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "chat":
        data_path = Path(args.db)
        log_path = Path(args.log)
        app = build_app(storage_path=data_path, audit_path=log_path, gateway=create_default_gateway())
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == "mcp":
        service = MCPService()
        asyncio.run(service.run())
    elif args.command == "gateway":
        asyncio.run(handle_gateway_command(args))


async def handle_gateway_command(args: argparse.Namespace) -> None:
    config = load_gateway_config(args.config)
    manager = GatewayManager()
    if args.gateway_command == "validate":
        print(f"Konfiguration '{args.config}' ist gültig und definiert {len(config.adapters)} Adapter")
    elif args.gateway_command == "list":
        await manager.reload_from_config(config)
        adapter_map = await manager.list_adapters()
        print("Registrierte Adapter:")
        for name, cls_name in adapter_map.items():
            print(f"- {name}: {cls_name}")
    elif args.gateway_command == "metrics":
        await manager.reload_from_config(config)
        snapshot = await manager.snapshot()
        print("Metriken:")
        for category, values in snapshot.items():
            print(f"{category}:")
            for key, value in values.items():
                print(f"  {key}: {value}")
    elif args.gateway_command == "send":
        try:
            metadata = json.loads(args.metadata) if args.metadata else {}
        except json.JSONDecodeError as exc:
            print(f"Ungültiges JSON in --metadata: {exc}")
            return
        if not isinstance(metadata, dict):
            print("--metadata muss ein JSON-Objekt (Dictionary) sein")
            return

        service = GatewayService(manager, config)
        message = ChatMessage(
            id=str(uuid.uuid4()),
            room=args.room,
            sender_id=args.sender_id,
            sender_type=args.sender_type,
            content=args.message,
            metadata=metadata,
            created_at=utcnow(),
            target_adapter=args.adapter,
        )

        try:
            response = await service.submit(args.adapter, message)
        except Exception as exc:
            print(f"Fehler beim Dispatch über Adapter '{args.adapter}': {exc}")
            raise SystemExit(1) from exc
        finally:
            await service.stop()

        print(f"Nachricht an Adapter '{args.adapter}' gesendet.")
        if response is None:
            print("Adapter lieferte keine Antwort (None).")
        else:
            formatted = json.dumps(response, indent=2, ensure_ascii=False)
            print("Antwort:")
            print(formatted)


if __name__ == "__main__":
    main()
