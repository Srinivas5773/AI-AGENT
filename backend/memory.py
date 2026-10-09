import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionMemoryManager:
    """Manages isolated session-based conversation memory."""

    def __init__(self, max_history_turns: int = 10):
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self.max_history_turns = max_history_turns

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the conversation history for a given session."""
        if not session_id:
            session_id = "default_session"
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        """Appends a message to session history, enforcing max history limit."""
        if not session_id:
            session_id = "default_session"

        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append({"role": role, "content": content})

        # Keep last 2 * max_history_turns messages (user + assistant pairs)
        max_messages = self.max_history_turns * 2
        if len(self._sessions[session_id]) > max_messages:
            self._sessions[session_id] = self._sessions[session_id][-max_messages:]

    def clear_session(self, session_id: str) -> bool:
        """Clears/resets history for a specific session."""
        if not session_id:
            session_id = "default_session"

        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared session history for session '{session_id}'.")
            return True
        return False


# Singleton Memory Instance
memory_manager = SessionMemoryManager()
