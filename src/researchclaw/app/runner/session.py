"""Chat session management."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class ChatSession:
    """Represents a single chat conversation session."""

    def __init__(
        self,
        session_id: str | None = None,
        title: str = "New Research Chat",
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.title = title
        self.created_at = time.time()
        self.updated_at = time.time()
        self.messages: list[dict[str, Any]] = []

    def add_message(self, role: str, content: str):
        self.messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": time.time(),
            },
        )
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatSession":
        session = cls(
            session_id=data["session_id"],
            title=data.get("title", ""),
        )
        session.created_at = data.get("created_at", time.time())
        session.updated_at = data.get("updated_at", time.time())
        session.messages = data.get("messages", [])
        return session


class SessionManager:
    """Manages chat sessions with filesystem persistence."""

    def __init__(self, sessions_dir: str | None = None):
        self.sessions_dir = Path(
            sessions_dir or (Path(WORKING_DIR) / "sessions"),
        )
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, ChatSession] = {}

    def create_session(self, title: str = "New Research Chat") -> ChatSession:
        session = ChatSession(title=title)
        self._sessions[session.session_id] = session
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self._load_session(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        for f in sorted(
            self.sessions_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        ):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "title": data.get("title", ""),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "message_count": len(data.get("messages", [])),
                    },
                )
            except Exception:
                continue
        return sessions

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()

    def _save_session(self, session: ChatSession):
        path = self.sessions_dir / f"{session.session_id}.json"
        path.write_text(
            json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_session(self, session_id: str) -> ChatSession | None:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session = ChatSession.from_dict(data)
            self._sessions[session_id] = session
            return session
        except Exception:
            return None
