"""
Simple memory saver for LangGraph compatibility.

This is a minimal implementation that provides the required interface
for LangGraph without complex database operations.
"""

from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig


class SimpleMemorySaver:
    """Simple memory saver for LangGraph compatibility."""

    def __init__(self):
        """Initialize the simple memory saver."""
        self._memory: Dict[str, Any] = {}

    def get_next_version(self, *args, **kwargs) -> int:
        """Get the next version number."""
        import time

        return int(time.time() * 1000)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[tuple]:
        """Get tuple from memory."""
        thread_id = config.get("thread_id")
        if thread_id and thread_id in self._memory:
            return (self._memory[thread_id], self.get_next_version(config))
        return None

    async def aput_writes(
        self, config: RunnableConfig, writes: List[Any], *args, **kwargs
    ) -> None:
        """Put writes to memory."""
        thread_id = config.get("thread_id")
        if thread_id and writes:
            # Store the last write
            self._memory[thread_id] = writes[-1] if writes else None

    async def get(self, config: RunnableConfig) -> Optional[Dict[str, Any]]:
        """Get state from memory."""
        thread_id = config.get("thread_id")
        if thread_id and thread_id in self._memory:
            return self._memory[thread_id]
        return None

    async def put(self, config: RunnableConfig, value: Any) -> None:
        """Put state to memory."""
        thread_id = config.get("thread_id")
        if thread_id:
            self._memory[thread_id] = value

    async def aput(
        self, config: RunnableConfig, value: Any, *args, **kwargs
    ) -> None:
        """Async put state to memory."""
        await self.put(config, value)

    def close(self) -> None:
        """Close memory saver."""
        self._memory.clear()

    def get_all_threads(self) -> List[Dict[str, Any]]:
        """Get all thread IDs."""
        return [{"thread_id": tid} for tid in self._memory.keys()]

    async def delete_thread(self, thread_id: str) -> None:
        """Delete thread from memory."""
        if thread_id in self._memory:
            del self._memory[thread_id]

    async def clear_thread(self, thread_id: str) -> None:
        """Clear thread from memory."""
        if thread_id in self._memory:
            del self._memory[thread_id]

    async def get_messages(
        self, thread_id: str, *args, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get messages for a thread."""
        if thread_id in self._memory:
            state = self._memory[thread_id]
            if isinstance(state, dict) and "messages" in state:
                return state["messages"]
        return []
