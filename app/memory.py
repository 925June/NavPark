import time
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID
from uuid import uuid4

from app.database import database


class MemoryStore:
    """Persist authenticated conversations and keep local eval history."""

    def __init__(self):
        self._sessions: Dict[str, List[Dict[str, str]]] = {}

    def create_session_id(self) -> str:
        return str(uuid4())

    def resolve_session(
        self,
        user_id: str,
        requested_session_id: Optional[str] = None,
    ) -> str:
        """Return a conversation owned by the user or create a new one."""
        requested = self._valid_session_id(requested_session_id)
        now = int(time.time())

        with database.connection() as connection:
            if requested:
                existing = connection.execute(
                    """
                    SELECT user_id
                    FROM conversations
                    WHERE id = ?
                    """,
                    (requested,),
                ).fetchone()
                if existing and existing["user_id"] == user_id:
                    return requested
                if existing:
                    requested = None

            session_id = requested or str(uuid4())
            connection.execute(
                """
                INSERT OR IGNORE INTO conversations(
                    id, user_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, now, now),
            )
            owner = connection.execute(
                "SELECT user_id FROM conversations WHERE id = ?",
                (session_id,),
            ).fetchone()
            if owner and owner["user_id"] != user_id:
                session_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO conversations(
                        id, user_id, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, now, now),
                )
            return session_id

    def get_history(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        if not user_id:
            return list(self._sessions.get(session_id, []))

        with database.connection() as connection:
            rows = connection.execute(
                """
                SELECT m.role, m.content
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE m.conversation_id = ? AND c.user_id = ?
                ORDER BY m.id
                """,
                (session_id, user_id),
            ).fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
        ]

    def append_turn(
        self,
        session_id: str,
        question: str,
        response: str,
        user_id: Optional[str] = None,
    ) -> None:
        if not user_id:
            history = self._sessions.setdefault(session_id, [])
            history.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": response},
            ])
            return

        now = int(time.time())
        with database.connection() as connection:
            conversation = connection.execute(
                """
                SELECT id
                FROM conversations
                WHERE id = ? AND user_id = ?
                """,
                (session_id, user_id),
            ).fetchone()
            if not conversation:
                raise ValueError(
                    "Conversation does not belong to the current user"
                )

            connection.executemany(
                """
                INSERT INTO messages(
                    conversation_id, role, content, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (session_id, "user", question, now),
                    (session_id, "assistant", response, now),
                ],
            )
            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )

    @staticmethod
    def _valid_session_id(session_id: Optional[str]) -> Optional[str]:
        if not session_id:
            return None
        try:
            return str(UUID(session_id))
        except (ValueError, AttributeError):
            return None


memory_store = MemoryStore()
