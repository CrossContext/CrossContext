"""
CrossContext - Multi-Turn Session Manager
Provides stateful conversation history with sliding window truncation
and context summarization for the autonomous agent loop.
"""

import time
from typing import Dict, Any, List, Optional


class SessionManager:
    """Manages multi-turn agent conversation state with memory-safe sliding window."""

    def __init__(self, max_messages: int = 20, max_tokens_estimate: int = 10000):
        """
        Args:
            max_messages: Maximum messages retained in conversation history before truncation.
            max_tokens_estimate: Approximate token threshold for triggering summarization.
        """
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Creates a new conversation session."""
        session = {
            "session_id": session_id,
            "messages": [],
            "created_at": time.time(),
            "last_active": time.time(),
            "turn_count": 0,
            "approx_tokens": 0,
            "summaries": [],
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an existing session by ID."""
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Returns existing session or creates a new one."""
        return self.get_session(session_id) or self.create_session(session_id)

    def add_message(self, session_id: str, role: str, content: Any) -> None:
        """
        Adds a message to the session history and applies sliding window truncation.

        Args:
            session_id: The session identifier.
            role: Message role ('user', 'assistant', 'system').
            content: Message content (string or list of content blocks).
        """
        session = self.get_or_create_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        session["messages"].append(message)
        session["last_active"] = time.time()
        session["turn_count"] += 1

        # Estimate token consumption
        content_str = str(content)
        session["approx_tokens"] += len(content_str) // 4

        # Apply sliding window if message count exceeds limit
        if len(session["messages"]) > self.max_messages:
            self._truncate_history(session_id)

        # Trigger summarization if token estimate exceeds threshold
        if session["approx_tokens"] > self.max_tokens_estimate:
            self._summarize_and_compact(session_id)

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Returns the current message history for the session."""
        session = self.get_session(session_id)
        if not session:
            return []
        return session["messages"]

    def get_context_for_model(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Returns a model-ready message list with any compacted summaries prepended.
        Suitable for passing directly to model_provider.invoke_with_tools().
        """
        session = self.get_session(session_id)
        if not session:
            return []

        context_messages = []

        # Prepend summaries of truncated history
        if session["summaries"]:
            summary_text = "\n".join(session["summaries"])
            context_messages.append({
                "role": "user",
                "content": f"[Prior conversation summary]: {summary_text}"
            })

        # Add current sliding window messages
        context_messages.extend(session["messages"])

        return context_messages

    def _truncate_history(self, session_id: str) -> None:
        """Removes oldest messages beyond the sliding window, preserving a summary."""
        session = self._sessions[session_id]
        excess = len(session["messages"]) - self.max_messages

        if excess <= 0:
            return

        # Extract messages that will be removed
        removed = session["messages"][:excess]

        # Generate a simple summary of removed messages
        summary_parts = []
        for msg in removed:
            role = msg["role"]
            content = str(msg["content"])[:200]
            summary_parts.append(f"[{role}]: {content}")

        truncation_summary = f"Truncated {len(removed)} messages. Content: " + " | ".join(summary_parts)
        session["summaries"].append(truncation_summary)

        # Remove excess messages
        session["messages"] = session["messages"][excess:]

    def _summarize_and_compact(self, session_id: str) -> None:
        """
        Compacts old messages when token budget is strained.
        Keeps the last N messages and summarizes the rest.
        """
        session = self._sessions[session_id]
        if len(session["messages"]) <= 1:
            return

        keep_count = max(1, min(self.max_messages // 2, len(session["messages"]) // 2))

        removed = session["messages"][:-keep_count]
        summary_parts = []
        for msg in removed:
            role = msg["role"]
            content = str(msg["content"])[:150]
            summary_parts.append(f"[{role}]: {content}")

        compaction_summary = f"Compacted {len(removed)} messages due to token budget. " + " | ".join(summary_parts)
        session["summaries"].append(compaction_summary)

        # Keep only recent messages and reset token counter
        session["messages"] = session["messages"][-keep_count:]
        session["approx_tokens"] = sum(len(str(m["content"])) // 4 for m in session["messages"])

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns metadata for all active sessions."""
        return [
            {
                "session_id": s["session_id"],
                "turn_count": s["turn_count"],
                "message_count": len(s["messages"]),
                "approx_tokens": s["approx_tokens"],
                "created_at": s["created_at"],
                "last_active": s["last_active"],
            }
            for s in self._sessions.values()
        ]

    def clear_session(self, session_id: str) -> bool:
        """Removes a session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
