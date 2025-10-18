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
            detail=(
                "Failed to retrieve conversation history. " "Please try again."
            ),
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
        await agent.memory_manager.clear_conversation(thread_id)

        return {
            "message": f"Thread {thread_id} cleared successfully",
            "thread_id": thread_id,
        }

    except Exception as e:
        logger.error(f"Error clearing conversation thread: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear conversation thread. Please try again.",
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
            status_code=500, detail="Failed to list threads. Please try again."
        )


@router.post("/test", response_model=Dict[str, str])
async def test_chat():
    """Simple test endpoint that doesn't use the agent."""
    return {"message": "Test endpoint working!", "status": "success"}


@router.post("/test-agent", response_model=Dict[str, str])
async def test_agent():
    """Test endpoint that tries to create agent without MCP client."""
    try:
        from adapters.llm import LLMFactory
        from config import settings

        # Test LLM creation
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            model="llama-3.1-8b-instant",
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
        from langchain_core.messages import HumanMessage

        from adapters.llm import LLMFactory
        from config import settings

        # Create LLM
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=2048,
        )

        # Simple chat
        messages = [
            HumanMessage(content="Hello! Can you help me with meal planning?")
        ]
        response = await llm.ainvoke(messages)

        return {
            "message": "Simple chat successful!",
            "status": "success",
            "response": (
                response.content[:100] + "..."
                if len(response.content) > 100
                else response.content
            ),
        }
    except Exception as e:
        return {
            "message": f"Error in simple chat: {str(e)}",
            "status": "error",
        }


@router.post("/simple-chat", response_model=ChatResponse)
async def simple_chat(request: ChatRequest):
    """Simple chat endpoint that uses LLM directly."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from adapters.llm import LLMFactory
        from config import settings

        # Create LLM
        llm = LLMFactory.create_llm(
            provider="groq",
            api_key=settings.groq_api_key,
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=2048,
        )

        # Create messages
        system_message = SystemMessage(
            content=(
                "You are a helpful chef assistant that helps with meal planning. "
                "Respond to user requests about cooking, recipes, and meal planning. "
                "Be friendly and helpful."
            )
        )
        human_message = HumanMessage(content=request.message)
        messages = [system_message, human_message]

        # Get response
        response = await llm.ainvoke(messages)

        return ChatResponse(
            message=response.content, thread_id=request.thread_id
        )

    except Exception as e:
        return ChatResponse(
            message=f"I apologize, but I encountered an error: {str(e)}",
            thread_id=request.thread_id,
        )
