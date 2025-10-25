from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar
from uuid import uuid4

import uvicorn

from .chat.server import build_app
from .chat.storage import utcnow
from .chat.models import ChatMessage
from .gateway.config import GatewayConfig, load_gateway_config
from .gateway.manager import GatewayManager, create_default_gateway
from .mcp.service import MCPService


_T = TypeVar("_T")


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

    dispatch_parser = gateway_sub.add_parser(
        "dispatch", help="Sendet eine Testnachricht an einen Adapter"
    )
    dispatch_parser.add_argument("--config", required=True, help="Pfad zur Gateway-Konfiguration")
    dispatch_parser.add_argument("--adapter", required=True, help="Name des Zieladapters")
    dispatch_parser.add_argument("--content", required=True, help="Nachrichteninhalt")
    dispatch_parser.add_argument("--room", default="lab", help="Chatraum-Kennung")
    dispatch_parser.add_argument("--sender-id", default="cli", help="Sender-ID")
    dispatch_parser.add_argument(
        "--sender-type",
        default="system",
        help="Sender-Typ (z. B. human, assistant, system)",
    )
    dispatch_parser.add_argument(
        "--metadata",
        default=None,
        help="Optionales JSON-Objekt mit zusätzlichen Metadaten",
    )
    dispatch_parser.add_argument(
        "--message-id",
        default=None,
        help="Optional vorgegebene Nachrichten-ID",
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
    if args.gateway_command == "validate":
        print(
            f"Konfiguration '{args.config}' ist gültig und definiert {len(config.adapters)} Adapter"
        )
        return

    if args.gateway_command == "list":

        async def _list(manager: GatewayManager) -> None:
            adapter_map = await manager.list_adapters()
            print("Registrierte Adapter:")
            for name, cls_name in adapter_map.items():
                print(f"- {name}: {cls_name}")

        await _with_gateway_manager(config, _list)
        return

    if args.gateway_command == "metrics":

        async def _metrics(manager: GatewayManager) -> None:
            snapshot = await manager.snapshot()
            print("Metriken:")
            for category, values in snapshot.items():
                print(f"{category}:")
                for key, value in values.items():
                    print(f"  {key}: {value}")

        await _with_gateway_manager(config, _metrics)
        return

    if args.gateway_command == "dispatch":
        try:
            metadata = _parse_metadata(args.metadata)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

        async def _dispatch(manager: GatewayManager) -> None:
            message = ChatMessage(
                id=args.message_id or str(uuid4()),
                room=args.room,
                sender_id=args.sender_id,
                sender_type=args.sender_type,
                content=args.content,
                metadata=metadata,
                created_at=utcnow(),
                target_adapter=args.adapter,
            )
            response = await manager.dispatch(args.adapter, message)
            if response is None:
                print("Adapter lieferte keine Antwort.")
            else:
                print(json.dumps(response, ensure_ascii=False))

        await _with_gateway_manager(config, _dispatch)
        return

    raise SystemExit(f"Unbekannter Gateway-Befehl: {args.gateway_command}")


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if raw in (None, ""):
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI-Eingabefehler
        raise ValueError(f"Metadaten sind kein gültiges JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Metadaten müssen ein JSON-Objekt sein")
    return value


async def _with_gateway_manager(
    config: GatewayConfig,
    action: Callable[[GatewayManager], Awaitable[_T]],
) -> _T:
    manager = GatewayManager()
    try:
        await manager.reload_from_config(config)
        return await action(manager)
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    main()
