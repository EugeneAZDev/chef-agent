"""
Memory system for the Chef Agent.

This module provides conversation memory functionality using SQLite
to store and retrieve conversation history for follow-up requests.
"""

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.models import AgentState


class SQLiteMemorySaver(BaseCheckpointSaver):
    """SQLite-based memory saver for LangGraph agent."""

    def __init__(self, db_path: str = "agent_memory.db"):
        """Initialize the memory saver."""
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
            # Set busy timeout to handle concurrent access
            self._connection.execute("PRAGMA busy_timeout = 5000;")
        return self._connection

    def _create_schema(self) -> None:
        """Create database schema for memory storage."""
        conn = self._get_connection()

        # Create conversations table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                thread_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create messages table for detailed message history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversations(thread_id)
                ON DELETE CASCADE
            )
        """
        )

        # Create indexes
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_thread_id "
            "ON messages(thread_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp "
            "ON messages(timestamp)"
        )

        conn.commit()

    async def get(self, config: RunnableConfig) -> Optional[Dict[str, Any]]:
        """Get checkpoint for a thread."""
        thread_id = config.get("thread_id")
        if not thread_id:
            return None

        async with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT state_data FROM conversations WHERE thread_id = ?",
                (thread_id,),
            )
            row = cursor.fetchone()

            if row:
                try:
                    return json.loads(row["state_data"])
                except (json.JSONDecodeError, KeyError):
                    return None

            return None

    async def put(
        self, config: RunnableConfig, checkpoint: Dict[str, Any]
    ) -> None:
        """Save checkpoint for a thread."""
        thread_id = config.get("thread_id")
        if not thread_id:
            return

        async with self._lock:
            conn = self._get_connection()
            state_data = json.dumps(checkpoint)

            conn.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    thread_id, state_data, updated_at
                )
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (thread_id, state_data),
            )

            conn.commit()

    async def add_message(
        self, thread_id: str, role: str, content: str
    ) -> None:
        """Add a message to the conversation history."""
        async with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT INTO messages (thread_id, role, content)
                VALUES (?, ?, ?)
            """,
                (thread_id, role, content),
            )
            conn.commit()

    async def get_messages(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, str]]:
        """Get recent messages for a thread."""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT role, content, timestamp
                FROM messages
                WHERE thread_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """,
                (thread_id, limit),
            )

            messages = []
            for row in cursor.fetchall():
                messages.append(
                    {
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                    }
                )

            return messages

    async def clear_thread(self, thread_id: str) -> None:
        """Clear all data for a thread."""
        async with self._lock:
            conn = self._get_connection()
            conn.execute(
                "DELETE FROM messages WHERE thread_id = ?", (thread_id,)
            )
            conn.execute(
                "DELETE FROM conversations WHERE thread_id = ?", (thread_id,)
            )
            conn.commit()

    async def get_thread_info(
        self, thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get thread information."""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT thread_id, created_at, updated_at,
                       COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.thread_id = m.thread_id
                WHERE c.thread_id = ?
                GROUP BY c.thread_id, c.created_at, c.updated_at
            """,
                (thread_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "thread_id": row["thread_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"],
                }

            return None

    def get_all_threads(self) -> List[Dict[str, Any]]:
        """Get all conversation threads."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT c.thread_id, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.thread_id = m.thread_id
            GROUP BY c.thread_id, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """
        )

        threads = []
        for row in cursor.fetchall():
            threads.append(
                {
                    "thread_id": row["thread_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"],
                }
            )

        return threads

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


class MemoryManager:
    """High-level memory management for the agent."""

    def __init__(self, db_path: str = "agent_memory.db"):
        """Initialize memory manager."""
        self.memory_saver = SQLiteMemorySaver(db_path)

    async def save_conversation_state(
        self, thread_id: str, state: AgentState
    ) -> None:
        """Save conversation state."""
        state_dict = state.model_dump()
        await self.memory_saver.put({"thread_id": thread_id}, state_dict)

    async def load_conversation_state(
        self, thread_id: str
    ) -> Optional[AgentState]:
        """Load conversation state."""
        state_dict = await self.memory_saver.get({"thread_id": thread_id})
        if state_dict:
            try:
                return AgentState(**state_dict)
            except Exception:
                return None
        return None

    async def add_user_message(self, thread_id: str, message: str) -> None:
        """Add user message to history."""
        await self.memory_saver.add_message(thread_id, "user", message)

    async def add_assistant_message(
        self, thread_id: str, message: str
    ) -> None:
        """Add assistant message to history."""
        await self.memory_saver.add_message(thread_id, "assistant", message)

    async def get_conversation_history(
        self, thread_id: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get conversation history."""
        return await self.memory_saver.get_messages(thread_id, limit)

    async def clear_conversation(self, thread_id: str) -> None:
        """Clear conversation history."""
        await self.memory_saver.clear_thread(thread_id)
