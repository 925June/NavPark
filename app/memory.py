from typing import Dict
from typing import List
from uuid import uuid4


class MemoryStore:

    def __init__(self):

        self._sessions: Dict[str, List[Dict[str, str]]] = {}

    def create_session_id(self) -> str:

        return str(uuid4())

    def get_history(self, session_id: str) -> List[Dict[str, str]]:

        return list(
            self._sessions.get(session_id, [])
        )

    def append_turn(
        self,
        session_id: str,
        question: str,
        response: str
    ) -> None:

        history = self._sessions.setdefault(
            session_id,
            []
        )

        history.extend([
            {
                "role": "user",
                "content": question
            },
            {
                "role": "assistant",
                "content": response
            }
        ])


memory_store = MemoryStore()