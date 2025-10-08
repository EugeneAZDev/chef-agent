"""
Chat API endpoints for Chef Agent.

This module provides REST API endpoints for chat functionality,
including message processing and conversation management.
"""

import logging
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from adapters.mcp.client import ChefAgentMCPClient
from agent.graph import ChefAgentGraph
from agent.models import ChatRequest, ChatResponse, ErrorResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def validate_thread_id(thread_id: str) -> str:
    """Validate thread_id format."""
    if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", thread_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid thread_id format. Must be 3-64 characters, "
            "alphanumeric, underscore, or dash only.",
        )
    return thread_id


# Global agent instance (will be initialized on startup)
_agent: ChefAgentGraph = None


def get_agent() -> ChefAgentGraph:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        try:
            from config import settings

            mcp_client = ChefAgentMCPClient()

            # Determine LLM provider and API key
            if settings.groq_api_key:
                llm_provider = "groq"
                api_key = settings.groq_api_key
            elif getattr(settings, "openai_api_key", None):
                llm_provider = "openai"
                api_key = settings.openai_api_key
            else:
                llm_provider = "groq"  # Default to groq
                api_key = "test-key"  # Will fail gracefully

            _agent = ChefAgentGraph(
                llm_provider=llm_provider,
                api_key=api_key,
                mcp_client=mcp_client,
            )
            logger.info("Chef Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chef Agent: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to initialize Chef Agent"
            )
    return _agent


@router.post(
    "/message",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send a message to the Chef Agent",
    description="Process a user message and get a response from Chef Agent",
)
async def send_message(
    request: ChatRequest, agent: ChefAgentGraph = Depends(get_agent)
) -> ChatResponse:
    """
    Send a message to the Chef Agent and get a response.

    This endpoint processes user messages and returns agent responses
    along with any generated meal plans or shopping lists.
    """
    try:
        logger.info(f"Processing message for thread {request.thread_id}")

        # Process the request through the agent
        response = agent.process_request(request)

        # Return the response directly (it's already a ChatResponse)
        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process message: {str(e)}"
        )


@router.get(
    "/threads/{thread_id}/history",
    response_model=Dict[str, Any],
    responses={
        404: {"model": ErrorResponse, "description": "Thread not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Get conversation history",
    description="Retrieve the conversation history for a specific thread",
)
async def get_conversation_history(
    thread_id: str = Depends(validate_thread_id),
    agent: ChefAgentGraph = Depends(get_agent),
) -> Dict[str, Any]:
    """
    Get the conversation history for a specific thread.

    Returns the complete conversation history including
    all messages and context for the given thread.
    """
    try:
        logger.info(f"Retrieving history for thread {thread_id}")

        # Get conversation history from agent memory
        logger.info(f"Calling get_conversation_history for thread {thread_id}")
        logger.info(f"Agent type: {type(agent)}")
        logger.info(f"Memory manager type: {type(agent.memory_manager)}")
        logger.info(
            f"get_conversation_history type: "
            f"{type(agent.memory_manager.get_conversation_history)}"
        )
        history = await agent.memory_manager.get_conversation_history(
            thread_id
        )
        logger.info(f"Got history: {history}")

        return {
            "thread_id": thread_id,
            "messages": history,
            "total_messages": len(history) if history else 0,
        }

    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}",
        )


@router.delete(
    "/threads/{thread_id}",
    response_model=Dict[str, str],
    responses={
        404: {"model": ErrorResponse, "description": "Thread not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Clear conversation thread",
    description="Clear all messages and context for a specific thread",
)
async def clear_conversation_thread(
    thread_id: str = Depends(validate_thread_id),
    agent: ChefAgentGraph = Depends(get_agent),
) -> Dict[str, str]:
    """
    Clear the conversation thread.

    Removes all messages and context for the specified thread,
    effectively starting a fresh conversation.
    """
    try:
        logger.info(f"Clearing thread {thread_id}")

        # Clear the conversation thread
        await agent.memory_manager.clear_thread(thread_id)

        return {
            "message": f"Thread {thread_id} cleared successfully",
            "thread_id": thread_id,
        }

    except Exception as e:
        logger.error(f"Error clearing conversation thread: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversation thread: {str(e)}",
        )


@router.get(
    "/threads",
    response_model=Dict[str, Any],
    summary="List active threads",
    description="Get a list of all active conversation threads",
)
async def list_threads(
    agent: ChefAgentGraph = Depends(get_agent),
) -> Dict[str, Any]:
    """
    List all active conversation threads.

    Returns a list of thread IDs and basic information
    about each active conversation.
    """
    try:
        logger.info("Listing active threads")

        # Get all threads from memory manager
        threads = agent.memory_manager.memory_saver.get_all_threads()

        return {
            "threads": threads,
            "total_threads": len(threads) if threads else 0,
        }

    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list threads: {str(e)}"
        )
