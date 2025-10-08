"""
LangGraph agent for the Chef Agent.

This module implements the main agent workflow using LangGraph
with nodes for planning, tool execution, and response generation.
"""

from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from adapters.llm import LLMFactory
from adapters.mcp.client import ChefAgentMCPClient
from agent.memory import MemoryManager
from agent.models import AgentState, ChatRequest, ChatResponse
from agent.tools import create_chef_tools
from prompts import prompt_loader


class ChefAgentGraph:
    """Main LangGraph agent for the Chef Agent."""

    def __init__(
        self,
        llm_provider: str,
        api_key: str,
        mcp_client: ChefAgentMCPClient,
        model: Optional[str] = None,
    ):
        """Initialize the agent graph."""
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.mcp_client = mcp_client
        self.memory_manager = MemoryManager()

        # Initialize LLM using factory
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            api_key=api_key,
            model=model,
            temperature=0.7,
            max_tokens=2048,
        )

        # Create tools
        self.tools = create_chef_tools(mcp_client)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Create tool node
        self.tool_node = ToolNode(self.tools)

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("responder", self._responder_node)

        # Add edges
        workflow.add_edge("planner", "tools")
        workflow.add_edge("tools", "responder")
        workflow.add_edge("responder", END)

        # Set entry point
        workflow.set_entry_point("planner")

        # Compile with memory
        return workflow.compile(checkpointer=self.memory_manager.memory_saver)

    async def _planner_node(self, state: AgentState) -> AgentState:
        """Plan the agent's actions based on user input."""
        try:
            # Extract user input
            user_message = self._extract_user_input(state)

            # Prepare messages for LLM
            messages = self._prepare_llm_messages(user_message, state.language)

            # Call LLM
            response = await self._call_llm(messages)

            # Update state with LLM response
            self._update_state_from_llm(state, response)

            return state

        except Exception as e:
            state.error = f"Planning error: {str(e)}"
            return state

    def _extract_user_input(self, state: AgentState) -> str:
        """Extract user message from state."""
        return state.messages[-1]["content"] if state.messages else ""

    def _prepare_llm_messages(self, user_message: str, language: str) -> list:
        """Prepare messages for LLM including system prompt."""
        system_prompt = self._create_system_prompt(language)

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

    async def _call_llm(self, messages: list) -> Any:
        """Call LLM with prepared messages."""
        return await self.llm_with_tools.ainvoke(messages)

    def _update_state_from_llm(self, state: AgentState, response: Any) -> None:
        """Update state with LLM response and extract tool calls."""
        # Add assistant message to state
        state.messages.append(
            {"role": "assistant", "content": response.content}
        )

        # Extract tool calls if any - replace instead of append to avoid
        # duplication
        if hasattr(response, "tool_calls") and response.tool_calls:
            state.tool_calls = response.tool_calls

    async def _tools_node(self, state: AgentState) -> AgentState:
        """Execute tool calls."""
        if not getattr(state, "tool_calls", None):
            return state

        # Execute tool calls
        tool_results = []
        for tool_call in state.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            try:
                # Find and execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                tool_results.append(tool_result)
            except Exception as e:
                # Log the error and add it to results
                error_result = {
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e),
                    "result": None,
                }
                tool_results.append(error_result)

                # Set error state to stop execution
                state.error = f"Tool '{tool_name}' execution failed: {str(e)}"
                state.tool_results = tool_results
                return state

        # Update state with tool results
        state.tool_results = tool_results
        return state

    async def _responder_node(self, state: AgentState) -> AgentState:
        """Generate final response based on tool results."""
        try:
            # Create response based on tool results
            response_content = await self._generate_response(state)

            # Update state
            state.messages.append(
                {"role": "assistant", "content": response_content}
            )

            return state

        except Exception as e:
            state.error = f"Response generation error: {str(e)}"
            return state

    async def _execute_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific tool."""
        try:
            # Find the tool
            tool_func = None
            for tool in self.tools:
                if tool.name == tool_name:
                    tool_func = tool
                    break

            if not tool_func:
                return {"error": f"Tool {tool_name} not found"}

            # Execute the tool
            result = tool_func.invoke(tool_args)
            return result

        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    async def _generate_response(self, state: AgentState) -> str:
        """Generate response based on current state."""
        try:
            # If there's an error, return error message
            if state.error:
                return (
                    f"I apologize, but I encountered an error: {state.error}"
                )

            # If we have tool results, process them
            if hasattr(state, "tool_results") and state.tool_results:
                return await self._process_tool_results(state)

            # Default response
            return (
                "I'm here to help you plan your meals! Please tell me about "
                "your dietary goals and how many days you'd like to plan for."
            )

        except Exception as e:
            return (
                f"I apologize, but I encountered an error while generating a "
                f"response: {str(e)}"
            )

    async def _process_tool_results(self, state: AgentState) -> str:
        """Process tool results and generate appropriate response."""
        try:
            response_parts = []

            for tool_result in state.tool_results:
                if tool_result.get("success"):
                    if "recipes" in tool_result:
                        # Handle recipe search results
                        recipes = tool_result["recipes"]
                        if recipes:
                            response_parts.append(
                                f"I found {len(recipes)} recipes for you:"
                            )
                            for i, recipe in enumerate(
                                recipes[:3], 1
                            ):  # Show first 3
                                response_parts.append(f"{i}. {recipe.title}")
                        else:
                            response_parts.append(
                                "I couldn't find any recipes matching your "
                                "criteria."
                            )

                    elif "shopping_list" in tool_result:
                        # Handle shopping list results
                        shopping_list = tool_result["shopping_list"]
                        if "items" in shopping_list and shopping_list["items"]:
                            response_parts.append(
                                f"I've added "
                                f"{len(shopping_list['items'])} items "
                                f"to your shopping list."
                            )
                        else:
                            response_parts.append(
                                "I've updated your shopping list."
                            )

                else:
                    # Handle tool errors
                    error_msg = tool_result.get("error", "Unknown error")
                    response_parts.append(
                        f"I encountered an issue: {error_msg}"
                    )

            return (
                "\\n\\n".join(response_parts)
                if response_parts
                else "I've completed the requested actions."
            )

        except Exception as e:
            return (
                f"I apologize, but I encountered an error while processing "
                f"the results: {str(e)}"
            )

    def _create_system_prompt(self, language: str = "en") -> str:
        """Create system prompt based on language."""
        return prompt_loader.get_system_prompt(language)

    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request and return a response."""
        try:
            # Create initial state
            initial_state = AgentState(
                thread_id=request.thread_id,
                messages=[{"role": "user", "content": request.message}],
                language=request.language,
            )

            # Process through the graph (LangGraph handles memory via
            # checkpointer)
            config = {"thread_id": request.thread_id}
            final_state = await self.graph.ainvoke(
                initial_state, config=config
            )

            # Extract response
            response_message = (
                final_state.messages[-1]["content"]
                if final_state.messages
                else "I apologize, but I couldn't process your request."
            )

            # Create response
            response = ChatResponse(
                message=response_message, thread_id=request.thread_id
            )

            # Add menu plan and shopping list if available
            if hasattr(final_state, "menu_plan") and final_state.menu_plan:
                response.menu_plan = final_state.menu_plan

            if (
                hasattr(final_state, "shopping_list")
                and final_state.shopping_list
            ):
                response.shopping_list = final_state.shopping_list

            return response

        except Exception as e:
            return ChatResponse(
                message=f"I apologize, but I encountered an error: {str(e)}",
                thread_id=request.thread_id,
            )

    async def close(self):
        """Close the agent and clean up resources."""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        self.memory_manager.memory_saver.close()
