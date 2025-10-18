from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..gateway.base import EchoAdapter
from ..gateway.manager import GatewayManager, create_default_gateway
from .audit import AuditLogger
from .models import Agent, ChatMessage
from .storage import ChatStorage, utcnow


class AgentCreate(BaseModel):
    name: str
    type: str = Field(description="Freitext, z. B. human, openai, local-llm")
    id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    room: str
    sender_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    target_adapter: Optional[str] = Field(
        default=None,
        description="Optionaler Name eines registrierten Gateway-Adapters",
    )


class MessageOut(BaseModel):
    id: str
    room: str
    sender_id: str
    sender_type: str
    content: str
    metadata: Dict[str, Any]
    created_at: str
    target_adapter: Optional[str]


class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    metadata: Dict[str, Any]
    created_at: str


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(room, []).append(websocket)

    async def disconnect(self, room: str, websocket: WebSocket) -> None:
        async with self._lock:
            if room in self._rooms and websocket in self._rooms[room]:
                self._rooms[room].remove(websocket)
                if not self._rooms[room]:
                    self._rooms.pop(room, None)

    async def broadcast(self, room: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._rooms.get(room, []))
        for socket in sockets:
            await socket.send_json(payload)


class Dependencies:
    def __init__(self, storage: ChatStorage, audit: AuditLogger, gateway: GatewayManager) -> None:
        self.storage = storage
        self.audit = audit
        self.gateway = gateway
        self.connections = ConnectionManager()


def build_app(
    storage_path: Path,
    audit_path: Path,
    gateway: Optional[GatewayManager] = None,
) -> FastAPI:
    storage = ChatStorage(storage_path)
    audit = AuditLogger(audit_path)
    gateway_manager = gateway or create_default_gateway()

    app = FastAPI(title="QR Local Communication Hub", version="0.1.0")
    deps = Dependencies(storage=storage, audit=audit, gateway=gateway_manager)

    @app.on_event("startup")
    async def configure_gateway() -> None:
        # EchoAdapter als sichere Fallback-Automation verfügbar machen
        await deps.gateway.register_adapter(EchoAdapter("echo"))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_dependencies() -> Dependencies:
        return deps

    @app.post("/agents", response_model=AgentOut)
    async def create_agent(payload: AgentCreate, ctx: Dependencies = Depends(get_dependencies)) -> AgentOut:
        agent_id = payload.id or str(uuid.uuid4())
        agent = Agent(
            id=agent_id,
            name=payload.name,
            type=payload.type,
            metadata=payload.metadata,
            created_at=utcnow(),
        )
        ctx.storage.register_agent(agent)
        ctx.audit.log("agent_registered", {"agent_id": agent.id, "type": agent.type, "metadata": agent.metadata})
        return AgentOut(
            id=agent.id,
            name=agent.name,
            type=agent.type,
            metadata=agent.metadata,
            created_at=agent.created_at.isoformat(),
        )

    @app.get("/agents", response_model=List[AgentOut])
    async def list_agents(ctx: Dependencies = Depends(get_dependencies)) -> List[AgentOut]:
        agents = ctx.storage.list_agents()
        return [
            AgentOut(
                id=agent.id,
                name=agent.name,
                type=agent.type,
                metadata=agent.metadata,
                created_at=agent.created_at.isoformat(),
            )
            for agent in agents
        ]

    @app.post("/messages", response_model=MessageOut)
    async def post_message(payload: MessageCreate, ctx: Dependencies = Depends(get_dependencies)) -> MessageOut:
        agent = ctx.storage.get_agent(payload.sender_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Sender unbekannt")
        message = ChatMessage(
            id=str(uuid.uuid4()),
            room=payload.room,
            sender_id=agent.id,
            sender_type=agent.type,
            content=payload.content,
            metadata=payload.metadata,
            created_at=utcnow(),
            target_adapter=payload.target_adapter,
        )
        ctx.storage.store_message(message)
        ctx.audit.log(
            "message_stored",
            {
                "message_id": message.id,
                "room": message.room,
                "sender_id": message.sender_id,
                "target_adapter": message.target_adapter,
            },
        )
        await deps.connections.broadcast(
            message.room,
            {
                "type": "message",
                "message": MessageOut(
                    id=message.id,
                    room=message.room,
                    sender_id=message.sender_id,
                    sender_type=message.sender_type,
                    content=message.content,
                    metadata=message.metadata,
                    created_at=message.created_at.isoformat(),
                    target_adapter=message.target_adapter,
                ).model_dump(),
            },
        )
        if message.target_adapter:
            try:
                response = await ctx.gateway.dispatch(message.target_adapter, message)
            except ValueError as exc:
                ctx.audit.log(
                    "gateway_error",
                    {
                        "message_id": message.id,
                        "error": str(exc),
                        "adapter": message.target_adapter,
                    },
                )
            else:
                if response:
                    ctx.audit.log(
                        "gateway_response",
                        {
                            "message_id": message.id,
                            "adapter": message.target_adapter,
                            "response": response,
                        },
                    )
        return MessageOut(
            id=message.id,
            room=message.room,
            sender_id=message.sender_id,
            sender_type=message.sender_type,
            content=message.content,
            metadata=message.metadata,
            created_at=message.created_at.isoformat(),
            target_adapter=message.target_adapter,
        )

    @app.get("/messages", response_model=List[MessageOut])
    async def list_messages(
        room: Optional[str] = None,
        limit: Optional[int] = None,
        ctx: Dependencies = Depends(get_dependencies),
    ) -> List[MessageOut]:
        messages = ctx.storage.list_messages(room=room, limit=limit)
        return [
            MessageOut(
                id=message.id,
                room=message.room,
                sender_id=message.sender_id,
                sender_type=message.sender_type,
                content=message.content,
                metadata=message.metadata,
                created_at=message.created_at.isoformat(),
                target_adapter=message.target_adapter,
            )
            for message in messages
        ]

    @app.websocket("/ws/{room}")
    async def websocket_endpoint(websocket: WebSocket, room: str, ctx: Dependencies = Depends(get_dependencies)) -> None:
        await ctx.connections.connect(room, websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                ctx.audit.log("ws_message", {"room": room, "payload": payload})
        except WebSocketDisconnect:
            await ctx.connections.disconnect(room, websocket)

    @app.get("/healthz")
    async def health() -> Dict[str, Any]:
        return {"status": "ok"}

    return app


__all__ = ["build_app"]
