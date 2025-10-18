from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Agent, ChatMessage


_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    room TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    sender_type TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    target_adapter TEXT NULL,
    FOREIGN KEY(sender_id) REFERENCES agents(id)
);
"""


class ChatStorage:
    """SQLite-basierte Persistenz für Chat-Agenten und Nachrichten."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def register_agent(self, agent: Agent) -> None:
        payload = asdict(agent)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO agents (id, name, type, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    payload["id"],
                    payload["name"],
                    payload["type"],
                    json.dumps(payload["metadata"], ensure_ascii=False, sort_keys=True),
                    payload["created_at"].isoformat(),
                ),
            )
            conn.commit()

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cur.fetchone()
        if not row:
            return None
        return Agent(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_agents(self) -> List[Agent]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM agents ORDER BY created_at ASC").fetchall()
        return [
            Agent(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def store_message(self, message: ChatMessage) -> None:
        payload = asdict(message)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, room, sender_id, sender_type, content, metadata, created_at, target_adapter)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["room"],
                    payload["sender_id"],
                    payload["sender_type"],
                    payload["content"],
                    json.dumps(payload["metadata"], ensure_ascii=False, sort_keys=True),
                    payload["created_at"].isoformat(),
                    payload["target_adapter"],
                ),
            )
            conn.commit()

    def list_messages(self, room: Optional[str] = None, limit: Optional[int] = None) -> List[ChatMessage]:
        query = "SELECT * FROM messages"
        params: List[object] = []
        if room:
            query += " WHERE room = ?"
            params.append(room)
        query += " ORDER BY created_at ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ChatMessage(
                id=row["id"],
                room=row["room"],
                sender_id=row["sender_id"],
                sender_type=row["sender_type"],
                content=row["content"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                target_adapter=row["target_adapter"],
            )
            for row in rows
        ]

    def export_messages(self) -> Iterable[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM messages ORDER BY created_at ASC").fetchall()
        for row in rows:
            yield ChatMessage(
                id=row["id"],
                room=row["room"],
                sender_id=row["sender_id"],
                sender_type=row["sender_type"],
                content=row["content"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                target_adapter=row["target_adapter"],
            )


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
