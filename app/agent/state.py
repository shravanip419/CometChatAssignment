from typing import List, Dict, Optional
import re
from app.models.schemas import Message


class SessionState:
    """
    Maintains multi-turn conversation memory for a single session.
    """
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.messages: List[Message] = []
        self.last_order_id: Optional[str] = None
        self.last_topic: Optional[str] = None

    def add_user_message(self, content: str):
        self.messages.append(Message(role="user", content=content))
        # Look for order IDs mentioned in user message
        match = re.search(r"ORD[-_]?\d+", content, re.IGNORECASE)
        if match:
            # normalize
            digits = re.search(r"\d+", match.group(0))
            if digits:
                self.last_order_id = f"ORD-{digits.group(0)}"

    def add_assistant_message(self, content: str):
        self.messages.append(Message(role="assistant", content=content))

    def get_history(self, max_turns: int = 6) -> List[Message]:
        return self.messages[-max_turns:]

    def get_contextual_query(self, current_query: str) -> str:
        """
        Synthesizes conversation history with the current query for retrieval if needed.
        """
        # If user asks a brief follow up like 'What about Canada?' or 'When will it arrive?'
        q_lower = current_query.lower().strip()
        
        # If previous query was about international shipping
        if ("what about" in q_lower or "how long" in q_lower or "does it" in q_lower or "can i" in q_lower) and len(self.messages) >= 2:
            prev_user_msgs = [m.content for m in self.messages[:-1] if m.role == "user"]
            if prev_user_msgs:
                last_user_query = prev_user_msgs[-1]
                return f"{last_user_query} -> {current_query}"
                
        return current_query


class SessionManager:
    """Manages active sessions in memory."""
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def get_or_create_session(self, session_id: str = "default") -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id)
        return self.sessions[session_id]
