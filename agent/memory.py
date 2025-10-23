"""
SQLite-based memory saver for LangGraph.

This module provides persistent memory storage for conversation state.
"""

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig


class SQLiteMemorySaver:
    """SQLite-based memory saver for LangGraph conversations."""

    def __init__(self, db_path: str = "agent_memory.db"):
        """Initialize the memory saver with database path."""
        self.db_path = db_path
        self._connection = None
        self._lock = asyncio.Lock()  # Use asyncio.Lock for async operations
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with thread safety."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Allow cross-thread access
                timeout=30.0,  # 30 second timeout
            )
            self._connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")
            # Enable foreign key constraints
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def get_next_version(self, *args, **kwargs) -> int:
        """Get the next version number for the given config."""
        # For simplicity, we'll use a timestamp-based version
        import time

        return int(time.time() * 1000)  # milliseconds since epoch

    async def aput_writes(
        self, config: RunnableConfig, writes: List[Any], *args, **kwargs
    ) -> None:
        """Async put writes for LangGraph compatibility."""
        # Extract thread_id from configurable section
        thread_id = None
        if "configurable" in config and isinstance(config["configurable"], dict):
            thread_id = config["configurable"].get("thread_id")
        else:
            thread_id = config.get("thread_id")
            
        if thread_id and writes:
            # Store the last write using our existing put method
            await self.put(config, writes[-1] if writes else None)
            print(f"DEBUG: SQLiteMemorySaver - saved state for thread {thread_id}")

    async def aget_tuple(self, config: RunnableConfig) -> Optional[tuple]:
        """Async get tuple for LangGraph compatibility."""
        # Extract thread_id from configurable section
        thread_id = None
        if "configurable" in config and isinstance(config["configurable"], dict):
            thread_id = config["configurable"].get("thread_id")
        else:
            thread_id = config.get("thread_id")
            
        print(f"DEBUG: SQLiteMemorySaver - aget_tuple called for thread {thread_id}")
        if thread_id:
            # Try to get state from our existing get method
            state = await self.get(config)
            if state:
                print(f"DEBUG: SQLiteMemorySaver - found state for thread {thread_id}: {state}")
                # Return tuple with (state, version) format expected by LangGraph
                return (state, self.get_next_version())
        print(f"DEBUG: SQLiteMemorySaver - no state found for thread {thread_id}")
        return None

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._connection = None

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

        # Create messages table with foreign key constraint
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversations (thread_id)
            )
        """
        )

        # Check if created_at column exists in messages table, if not add it
        try:
            conn.execute("SELECT created_at FROM messages LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it with a constant default
            conn.execute(
                "ALTER TABLE messages ADD COLUMN created_at TIMESTAMP "
                "DEFAULT '1970-01-01 00:00:00'"
            )
            # Update existing rows with current timestamp
            conn.execute(
                "UPDATE messages SET created_at = CURRENT_TIMESTAMP "
                "WHERE created_at = '1970-01-01 00:00:00'"
            )

        # Create indexes for better performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
        )

        conn.commit()

    async def get(self, config: RunnableConfig) -> Optional[Dict[str, Any]]:
        """Get checkpoint for a thread."""
        # Extract thread_id from configurable section
        thread_id = None
        if "configurable" in config and isinstance(config["configurable"], dict):
            thread_id = config["configurable"].get("thread_id")
        else:
            thread_id = config.get("thread_id")
            
        if not thread_id:
            return None

        async with self._lock:
            # Use thread-safe database operations
            conn = self._get_connection()
            # Execute in a thread-safe manner
            import asyncio

            loop = asyncio.get_event_loop()
            row = await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    "SELECT state_data FROM conversations WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone(),
            )

            if row:
                try:
                    state_dict = json.loads(row["state_data"])
                    # Convert dict back to AgentState if needed
                    if isinstance(state_dict, dict) and "thread_id" in state_dict:
                        from agent.models import AgentState
                        return AgentState(**state_dict)
                    return state_dict
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"DEBUG: SQLiteMemorySaver - error deserializing state: {e}")
                    return None
            return None

    async def put(
        self, config: RunnableConfig, checkpoint: Dict[str, Any]
    ) -> None:
        """Save checkpoint for a thread."""
        # Extract thread_id from configurable section
        thread_id = None
        if "configurable" in config and isinstance(config["configurable"], dict):
            thread_id = config["configurable"].get("thread_id")
        else:
            thread_id = config.get("thread_id")
            
        if not thread_id:
            return

        async with self._lock:
            conn = self._get_connection()
            
            # Convert AgentState to dict if needed
            if hasattr(checkpoint, 'dict'):
                state_data = json.dumps(checkpoint.dict())
            elif hasattr(checkpoint, 'model_dump'):
                state_data = json.dumps(checkpoint.model_dump())
            else:
                state_data = json.dumps(checkpoint)

            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    """
                    INSERT OR REPLACE INTO conversations (
                        thread_id, state_data, updated_at
                    )
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (thread_id, state_data),
                ),
            )
            await loop.run_in_executor(None, conn.commit)

    async def aput(
        self, config: RunnableConfig, checkpoint: Dict[str, Any], *args, **kwargs
    ) -> None:
        """Async put checkpoint for a thread."""
        await self.put(config, checkpoint)

    async def add_message(
        self, thread_id: str, role: str, content: str
    ) -> None:
        """Add a message to the conversation history."""
        if not thread_id or not role or not content:
            return

        async with self._lock:
            conn = self._get_connection()

            # Ensure conversation exists first
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    "INSERT OR IGNORE INTO conversations "
                    "(thread_id, state_data) VALUES (?, ?)",
                    (thread_id, "{}"),
                ),
            )

            # Add message
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    """
                    INSERT INTO messages (thread_id, role, content)
                    VALUES (?, ?, ?)
                """,
                    (thread_id, role, content),
                ),
            )

            # Cleanup old messages to prevent memory leaks
            await self._cleanup_old_messages(thread_id)

            await loop.run_in_executor(None, conn.commit)

    async def _cleanup_old_messages(self, thread_id: str) -> None:
        """Clean up old messages to prevent memory leaks."""
        conn = self._get_connection()
        import asyncio

        loop = asyncio.get_event_loop()

        # Keep only the last 100 messages per thread
        await loop.run_in_executor(
            None,
            lambda: conn.execute(
                """
                DELETE FROM messages
                WHERE thread_id = ? AND id NOT IN (
                    SELECT id FROM messages
                    WHERE thread_id = ?
                    ORDER BY created_at DESC
                    LIMIT 100
                )
            """,
                (thread_id, thread_id),
            ),
        )

    async def get_messages(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages for a thread."""
        if not thread_id:
            return []

        async with self._lock:
            conn = self._get_connection()
            import asyncio

            loop = asyncio.get_event_loop()

            rows = await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    """
                    SELECT role, content, created_at
                    FROM messages
                    WHERE thread_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (thread_id, limit),
                ).fetchall(),
            )

            return [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_all_threads(self) -> List[Dict[str, Any]]:
        """Get all conversation threads (synchronous for compatibility)."""
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT thread_id, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
        """
        ).fetchall()

        return [
            {
                "thread_id": row["thread_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    async def delete_thread(self, thread_id: str) -> None:
        """Delete a conversation thread and all its messages."""
        if not thread_id:
            return

        async with self._lock:
            conn = self._get_connection()
            import asyncio

            loop = asyncio.get_event_loop()

            # Delete messages first (foreign key constraint)
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    "DELETE FROM messages WHERE thread_id = ?", (thread_id,)
                ),
            )

            # Delete conversation
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    "DELETE FROM conversations WHERE thread_id = ?",
                    (thread_id,),
                ),
            )

            await loop.run_in_executor(None, conn.commit)

    async def clear_thread(self, thread_id: str) -> None:
        """Clear all messages for a thread (alias for delete_thread)."""
        await self.delete_thread(thread_id)

    def close_connection(self) -> None:
        """Close database connection (alias for close method)."""
        self.close()

    async def delete_thread(self, thread_id: str) -> None:
        """Delete thread from memory."""
        async with self._lock:
            conn = self._get_connection()
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: conn.execute(
                    "DELETE FROM conversations WHERE thread_id = ?",
                    (thread_id,),
                ),
            )
            await loop.run_in_executor(None, conn.commit)

    async def clear_thread(self, thread_id: str) -> None:
        """Clear thread from memory."""
        await self.delete_thread(thread_id)

    def get_all_threads(self) -> List[Dict[str, Any]]:
        """Get all thread IDs."""
        conn = self._get_connection()
        rows = conn.execute("SELECT thread_id FROM conversations").fetchall()
        return [{"thread_id": row["thread_id"]} for row in rows]


class MemoryManager:
    """Memory manager for Chef Agent."""

    def __init__(self, db_path: str = "agent_memory.db"):
        """Initialize memory manager."""
        self.memory_saver = SQLiteMemorySaver(db_path)

    async def add_message(
        self, thread_id: str, role: str, content: str
    ) -> None:
        """Add a message to conversation history."""
        await self.memory_saver.add_message(thread_id, role, content)

    async def get_messages(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages for a thread."""
        return await self.memory_saver.get_messages(thread_id, limit)

    async def cleanup_old_messages(self, thread_id: str) -> None:
        """Clean up old messages to prevent memory leaks."""
        await self.memory_saver._cleanup_old_messages(thread_id)

    async def save_conversation_state(
        self, thread_id: str, state: Dict[str, Any]
    ) -> None:
        """Save conversation state."""
        await self.memory_saver.put({"thread_id": thread_id}, state)

    async def load_conversation_state(
        self, thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load conversation state."""
        return await self.memory_saver.get({"thread_id": thread_id})

    async def add_user_message(self, thread_id: str, content: str) -> None:
        """Add a user message."""
        await self.add_message(thread_id, "user", content)

    async def add_assistant_message(
        self, thread_id: str, content: str
    ) -> None:
        """Add an assistant message."""
        await self.add_message(thread_id, "assistant", content)

    async def clear_conversation(self, thread_id: str) -> None:
        """Clear conversation thread."""
        await self.memory_saver.clear_thread(thread_id)

    async def get_conversation_history(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a thread."""
        return await self.get_messages(thread_id, limit)

    def close(self) -> None:
        """Close memory manager and database connections."""
        self.memory_saver.close()
