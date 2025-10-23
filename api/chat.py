"""
Chat API endpoints for Chef Agent.

This module provides REST API endpoints for chat functionality,
including message processing and conversation management.
"""

import logging
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from adapters.i18n import translate
from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent import ChefAgentGraph
from agent.models import ChatRequest, ChatResponse, ErrorResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Global agent instance (will be initialized on startup)
_agent: ChefAgentGraph = None


def get_agent() -> ChefAgentGraph:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        try:
            from config import settings

            # Create MCP client
            mcp_client = ChefAgentHTTPMCPClient()

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


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    language: str = Query(
        "en", description="Language code (en, ru, es, fr, de)"
    ),
    agent: ChefAgentGraph = Depends(get_agent),
) -> ChatResponse:
    """
    Process a chat message and return a response.

    This endpoint handles user messages and returns AI responses
    with support for multiple languages.
    """
    try:
        # Override language from request if provided
        if hasattr(request, "language") and request.language:
            language = request.language

        # Process the request
        response = await agent.process_request(request)

        # Add language support to response
        if hasattr(response, "message"):
            response.message = translate("welcome", language)

        return response

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        error_msg = translate("error_occurred", language)
        raise HTTPException(status_code=500, detail=f"{error_msg}: {str(e)}")


def validate_thread_id(thread_id: str) -> str:
    """Validate thread_id format."""
    if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", thread_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid thread_id format. Must be 3-64 characters, "
            "alphanumeric, underscore, or dash only.",
        )
    return thread_id


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
        response = await agent.process_request(request)

        # Return the response directly (it's already a ChatResponse)
        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process message. Please try again.",
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
    all messages and tool calls for the thread.
    """
    try:
        # Get conversation history from memory
        history = await agent.memory_manager.get_conversation_history(
            thread_id
        )

        if not history:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Handle both list and dict responses
        if isinstance(history, list):
            messages = history
        else:
            messages = history.get("messages", [])

        return {
            "thread_id": thread_id,
            "history": messages,
            "message_count": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history",
        )


@router.post("/simple-chat", response_model=ChatResponse)
async def simple_chat(request: ChatRequest) -> ChatResponse:
    """
    Simple chat endpoint that provides basic responses without full agent.

    This endpoint is useful for testing basic functionality
    without the complexity of the full agent workflow.
    """
    try:
        from adapters.llm import LLMFactory
        from config import settings

        # Create a simple LLM instance
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            temperature=0.7,
            max_tokens=2048,
        )

        # Create a simple prompt
        prompt = f"""You are a helpful cooking assistant.
        The user said: "{request.message}"

        Please provide helpful cooking advice, recipe suggestions,
        or meal planning tips based on their request.

        Be friendly and informative in your response."""

        # Get response from LLM
        response = await llm.ainvoke(prompt)

        return ChatResponse(
            message=response.content,
            thread_id=request.thread_id,
        )

    except Exception as e:
        logger.error(f"Error in simple chat: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process simple chat request",
        )


@router.post("/test-agent", response_model=Dict[str, str])
async def test_agent():
    """Test endpoint to verify agent initialization."""
    try:
        from adapters.llm import LLMFactory
        from config import settings

        # Test LLM creation
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            temperature=0.7,
            max_tokens=2048,
        )

        return {
            "message": "LLM created successfully!",
            "status": "success",
            "llm_type": str(type(llm)),
        }

    except Exception as e:
        return {"message": f"Error creating LLM: {str(e)}", "status": "error"}


@router.post("/test-agent-no-mcp", response_model=Dict[str, str])
async def test_agent_no_mcp():
    """Test endpoint that creates agent without MCP client."""
    try:
        from agent import ChefAgentGraph
        from config import settings

        # Create agent without MCP client
        agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=None,  # No MCP client
            model="llama-3.1-8b-instant",
        )

        return {
            "message": "Agent created successfully without MCP!",
            "status": "success",
            "agent_type": str(type(agent)),
            "tools_count": str(len(agent.tools)),
        }
    except Exception as e:
        return {
            "message": f"Error creating agent: {str(e)}",
            "status": "error",
        }


@router.post("/test-simple-chat", response_model=Dict[str, str])
async def test_simple_chat():
    """Test simple chat without full agent."""
    try:
        from adapters.llm import LLMFactory
        from config import settings

        # Create LLM
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            temperature=0.7,
            max_tokens=2048,
        )

        # Test simple prompt
        prompt = "Hello! Can you help me with cooking?"
        response = await llm.ainvoke(prompt)

        return {
            "message": "Simple chat test successful!",
            "status": "success",
            "response": response.content[:100] + "...",
        }

    except Exception as e:
        return {
            "message": f"Error in simple chat test: {str(e)}",
            "status": "error",
        }


@router.get(
    "/threads",
    response_model=Dict[str, Any],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="List all chat threads",
    description="Retrieve a list of all chat threads with metadata",
)
async def list_threads(
    agent: ChefAgentGraph = Depends(get_agent),
) -> Dict[str, Any]:
    """
    List all chat threads.

    Returns a summary of all chat threads including
    thread_id, creation time, and message count.
    """
    try:
        # Get all threads from memory
        threads = agent.memory_manager.memory_saver.get_all_threads()

        return {
            "threads": threads,
            "total_threads": len(threads),
        }

    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve threads",
        )


@router.delete(
    "/threads/{thread_id}",
    response_model=Dict[str, str],
    responses={
        404: {"model": ErrorResponse, "description": "Thread not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Clear conversation thread",
    description="Clear all messages from a specific thread",
)
async def clear_conversation_thread(
    thread_id: str = Depends(validate_thread_id),
    agent: ChefAgentGraph = Depends(get_agent),
) -> Dict[str, str]:
    """
    Clear all messages from a specific thread.

    This endpoint removes all conversation history
    for the specified thread.
    """
    try:
        # Clear conversation from memory
        await agent.memory_manager.clear_conversation(thread_id)

        return {
            "message": f"Thread {thread_id} cleared successfully",
            "thread_id": thread_id,
        }

    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear conversation",
        )
