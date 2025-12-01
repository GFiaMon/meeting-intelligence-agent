"""
Meeting Intelligence Agent with Tool Support

This module implements a LangGraph-based meeting intelligence agent that uses tools to
interact with meeting transcripts for business use cases.

The agent is designed to:
- Quickly retrieve specific information from meeting transcripts
- Provide actionable summaries and extract action items
- Track decisions, speakers, and key discussion points
- Enable efficient cross-meeting analysis
"""

from typing import List, Dict, Any, Generator, TypedDict, Optional, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import Config
from core.tools import search_meetings, get_meeting_metadata, list_recent_meetings, initialize_tools


class MeetingAgentState(TypedDict):
    """State for the meeting intelligence agent graph."""
    message: str                          # Current user query
    history: List[List[str]]              # Conversation history [[user, bot], ...]
    llm_messages: Annotated[List[Any], add_messages]  # LLM messages for streaming
    response: str                         # Generated response
    error: Optional[str]                  # Error message if any


class MeetingIntelligenceAgent:
    """
    LangGraph-based meeting intelligence agent with tool-calling capabilities.
    
    This agent uses tools to help business users efficiently access and analyze
    information from their recorded meetings.
    """
    
    # Business meeting assistant system prompt
    SYSTEM_PROMPT = """You are an expert meeting intelligence assistant for business professionals. Your role is to help users efficiently access and analyze information from their recorded meetings.

**Your Core Functions:**

1. **Information Retrieval**: Quickly find specific information from meeting transcripts
2. **Meeting Summaries**: Provide concise, actionable summaries of meetings
3. **Action Item Extraction**: Identify and list action items, decisions, and next steps
4. **Speaker Attribution**: Track who said what and when
5. **Cross-Meeting Analysis**: Compare and synthesize information across multiple meetings

**Available Tools:**

You have access to three tools to help you:
- `search_meetings`: Search meeting transcripts semantically for specific information
- `get_meeting_metadata`: Get details about a specific meeting (date, participants, duration)
- `list_recent_meetings`: See what meetings are available in the system

**When to Use Tools:**

- Use `list_recent_meetings` when users ask "what meetings do I have?" or need to see available meetings
- Use `search_meetings` for specific questions about meeting content (action items, decisions, discussions)
- Use `get_meeting_metadata` when users want details about a particular meeting
- You can use multiple tools in sequence to build comprehensive answers

**Response Guidelines:**

- **Be Concise**: Business users value brevity - get to the point quickly
- **Be Specific**: Include concrete details (names, dates, action items)
- **Use Structure**: Format responses with headers, bullets, and numbered lists for scannability
- **Cite Sources**: Reference which meeting(s) information came from
- **Highlight Actions**: Emphasize action items, decisions, and deadlines

**Response Format for Common Queries:**

For summaries:
```
## Meeting Summary: [Meeting ID/Date]
**Key Decisions:**
- [Decision 1]
- [Decision 2]

**Action Items:**
1. [Action] - Owner: [Name] - Due: [Date]
2. [Action] - Owner: [Name] - Due: [Date]

**Next Steps:**
- [Next step]
```

For specific questions:
```
[Direct answer]

**Source:** Meeting [ID] on [Date]
**Context:** [Brief relevant context if needed]
```

Remember: You're a business tool focused on efficiency, accuracy, and actionable insights from meeting data."""

    def __init__(self, pinecone_manager):
        """
        Initialize the teaching agent.
        
        Args:
            pinecone_manager: Instance of PineconeManager for database access
        """
        self.pinecone_mgr = pinecone_manager
        
        # Initialize tools with the pinecone manager
        initialize_tools(pinecone_manager)
        
        # Create LLM with tool binding
        self.tools = [search_meetings, get_meeting_metadata, list_recent_meetings]
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY,
            streaming=False
        ).bind_tools(self.tools)
        
        # Build the state graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Builds the LangGraph state graph with tool support."""
        workflow = StateGraph(MeetingAgentState)
        
        # Add nodes
        workflow.add_node("prepare", self._prepare_messages)
        workflow.add_node("agent", self._call_agent)
        workflow.add_node("tools", ToolNode(self.tools, messages_key="llm_messages"))
        
        # Define edges
        workflow.set_entry_point("prepare")
        workflow.add_edge("prepare", "agent")
        
        # Conditional edge: if agent calls tools, go to tools node; otherwise end
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        # After tools, go back to agent
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _prepare_messages(self, state: MeetingAgentState) -> MeetingAgentState:
        """
        Node 1: Prepare LLM messages from conversation history.
        """
        try:
            llm_messages = [
                SystemMessage(content=self.SYSTEM_PROMPT)
            ]
            
            # Add conversation history - handle different Gradio formats
            for item in state["history"]:
                # Handle tuple/list format: [user_msg, assistant_msg]
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    user_msg, assistant_msg = item
                    if user_msg:
                        llm_messages.append(HumanMessage(content=user_msg))
                    if assistant_msg:
                        llm_messages.append(AIMessage(content=assistant_msg))
                # Handle dict format: {"role": "user", "content": "..."}
                elif isinstance(item, dict):
                    role = item.get("role")
                    content = item.get("content")
                    if role == "user" and content:
                        llm_messages.append(HumanMessage(content=content))
                    elif role == "assistant" and content:
                        llm_messages.append(AIMessage(content=content))
            
            # Add current query
            llm_messages.append(HumanMessage(content=state["message"]))
            
            return {"llm_messages": llm_messages}
            
        except Exception as e:
            return {"error": f"Error preparing messages: {str(e)}"}
    
    def _call_agent(self, state: MeetingAgentState) -> Dict[str, Any]:
        """
        Node 2: Call the LLM agent (may invoke tools).
        """
        if state.get("error"):
            return {}
        
        try:
            llm_messages = state["llm_messages"]
            # print(f"DEBUG: Calling LLM with {len(llm_messages)} messages")
            
            response = self.llm.invoke(llm_messages)
            
            # print(f"DEBUG: LLM Response: content='{response.content}', tool_calls={response.tool_calls}")
            
            # Return the new message to be appended
            return {"llm_messages": [response]}
            
        except Exception as e:
            print(f"ERROR in _call_agent: {str(e)}")
            return {"error": f"Error calling agent: {str(e)}"}
    
    def _should_continue(self, state: MeetingAgentState) -> str:
        """
        Conditional edge: Determine if we should continue to tools or end.
        """
        if state.get("error"):
            return "end"
        
        last_message = state["llm_messages"][-1]
        
        # If the last message has tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        return "end"
    
    def generate_response(self, message: str, history: List[List[str]]) -> Generator[str, None, None]:
        """
        Main entry point - generates a streaming response using the meeting intelligence agent.
        
        Args:
            message: The user's current message
            history: Conversation history in Gradio format [[user, bot], ...]
        
        Yields:
            Streaming response strings
        """
        # Initialize state
        initial_state: MeetingAgentState = {
            "message": message,
            "history": history,
            "llm_messages": [],
            "response": "",
            "error": None
        }
        
        try:
            # Run the graph
            final_state = self.graph.invoke(initial_state)
            
            # Check for errors
            if final_state.get("error"):
                yield final_state["error"]
                return
            
            # Extract the final response
            llm_messages = final_state.get("llm_messages", [])
            if not llm_messages:
                yield "Error: No response generated"
                return
            
            # Find the last AIMessage (the final response)
            final_response = None
            for msg in reversed(llm_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    final_response = msg.content
                    break
            
            if final_response:
                # Stream the response character by character for a smooth UX
                # (In production, you'd use actual streaming from the LLM)
                yield final_response
            else:
                yield "Error: No response content found"
                
        except Exception as e:
            yield f"Error generating response: {str(e)}"


# Alias for backward compatibility and clarity
RagAgentWithTools = MeetingIntelligenceAgent
