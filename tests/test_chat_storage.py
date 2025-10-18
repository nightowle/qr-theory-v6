from __future__ import annotations

from pathlib import Path

from qr_automation.chat.models import Agent, ChatMessage
from qr_automation.chat.storage import ChatStorage, utcnow


def create_storage(tmp_path: Path) -> ChatStorage:
    return ChatStorage(tmp_path / "chat.db")


def test_agent_registration_and_lookup(tmp_path: Path) -> None:
    storage = create_storage(tmp_path)
    agent = Agent(id="agent-1", name="Blue", type="human", metadata={}, created_at=utcnow())
    storage.register_agent(agent)

    loaded = storage.get_agent("agent-1")
    assert loaded is not None
    assert loaded.id == agent.id
    assert loaded.name == agent.name


def test_message_persistence(tmp_path: Path) -> None:
    storage = create_storage(tmp_path)
    agent = Agent(id="agent-2", name="NightOwl", type="ai", metadata={}, created_at=utcnow())
    storage.register_agent(agent)
    message = ChatMessage(
        id="msg-1",
        room="lab",
        sender_id=agent.id,
        sender_type=agent.type,
        content="Test",
        metadata={"k": "v"},
        created_at=utcnow(),
        target_adapter=None,
    )
    storage.store_message(message)
    messages = storage.list_messages(room="lab")
    assert len(messages) == 1
    assert messages[0].content == "Test"
