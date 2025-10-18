from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import uvicorn

from .chat.server import build_app
from .gateway.manager import create_default_gateway
from .mcp.service import MCPService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QR Automation Platform Launcher")
    parser.add_argument("command", choices=["chat", "mcp"], help="Komponente, die gestartet werden soll")
    parser.add_argument("--db", default="./data/chat.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--log", default="./logs/audit.jsonl", help="Audit-Log-Datei")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.db)
    log_path = Path(args.log)

    if args.command == "chat":
        app = build_app(storage_path=data_path, audit_path=log_path, gateway=create_default_gateway())
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == "mcp":
        service = MCPService()
        asyncio.run(service.run())


if __name__ == "__main__":
    main()
