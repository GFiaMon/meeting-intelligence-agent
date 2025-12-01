"""
Conversational Meeting Intelligence Agent

This module implements a LangGraph-based conversational agent that orchestrates
the entire meeting intelligence workflow through natural conversation, including:
- Video upload and transcription
- Transcription editing
- Pinecone storage
- Meeting queries and analysis
"""

from typing import List, Dict, Any, Generator, TypedDict, Optional, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import Config
from core.tools import search_meetings, get_meeting_metadata, list_recent_meetings, initialize_tools
from core.video_tools import (
    request_video_upload,
    transcribe_uploaded_video,
    request_transcription_edit,
    update_transcription,
    upload_transcription_to_pinecone,
    cancel_video_workflow,
    initialize_video_tools
)


class ConversationalAgentState(TypedDict):
    """State for the conversational meeting intelligence agent."""
    message: str                          # Current user query
    history: List[List[str]]              # Conversation history [[user, bot], ...]
    llm_messages: Annotated[List[Any], add_messages]  # LLM messages for streaming
    response: str                         # Generated response
    error: Optional[str]                  # Error message if any


class ConversationalMeetingAgent:
    """
    LangGraph-based conversational agent that manages the entire meeting intelligence workflow.
    
    This agent combines video processing tools with meeting query tools to provide
    a seamless conversational interface for all meeting-related tasks.
    """
    
    # Enhanced system prompt for conversational workflow
    SYSTEM_PROMPT = """You are a friendly and helpful Meeting Intelligence Assistant. You help users manage their meeting recordings through natural conversation.

**Your Capabilities:**

You can help users with two main workflows:

1. **Video Upload & Transcription Workflow**
   - Upload meeting videos
   - Transcribe with speaker identification
   - Edit transcriptions if needed
   - Store in Pinecone for AI-powered search

2. **Meeting Query & Analysis Workflow**
   - Search across meeting transcripts
   - Summarize meetings and extract key points
   - Find action items and decisions
   - Track speakers and discussions

**Available Tools:**

**Video Processing:**
- `request_video_upload`: Show video upload interface
- `transcribe_uploaded_video`: Process and transcribe video
- `request_transcription_edit`: Allow manual transcription editing
- `update_transcription`: Save edited transcription
- `upload_transcription_to_pinecone`: Store transcription in database
- `cancel_video_workflow`: Cancel current video workflow

**Meeting Queries:**
- `list_recent_meetings`: Show available meetings
- `search_meetings`: Search meeting content semantically
- `get_meeting_metadata`: Get meeting details

**Conversational Guidelines:**

1. **Start with a Greeting**: When the conversation begins, greet the user warmly and ask "What would you like to do today?"

2. **Guide the User**: Offer clear options:
   - "Would you like to upload a new meeting video?"
   - "Or would you prefer to search through your existing meetings?"

3. **Video Upload Flow**:
   - When user wants to upload: call `request_video_upload`
   - After upload: call `transcribe_uploaded_video` with the video path
   - Show transcription and ask: "Would you like to upload this to Pinecone or edit it first?"
   - If edit: call `request_transcription_edit`
   - After editing or if ready: call `upload_transcription_to_pinecone`
   - Confirm success and offer to help with queries

4. **Meeting Query Flow**:
   - For "what meetings": call `list_recent_meetings`
   - For specific questions: call `search_meetings`
   - For meeting details: call `get_meeting_metadata`
   - Provide clear, actionable answers

5. **Be Conversational**:
   - Use friendly, natural language
   - Acknowledge user actions ("Great! I'll transcribe that for you...")
   - Provide context and next steps
   - Ask clarifying questions when needed

6. **Handle Transitions**:
   - After completing video upload, smoothly transition to offering query capabilities
   - Allow users to switch between workflows naturally

**Response Format:**

Keep responses concise and actionable. Use:
- ✅ for success messages
- ❌ for errors
- 📹 for video-related actions
- 💬 for meeting queries
- 📊 for summaries and data

**Example Conversations:**

```
User: Hi
Agent: Hello! 👋 I'm your Meeting Intelligence Assistant. I can help you:
- 📹 Upload and transcribe meeting videos
- 💬 Search and analyze your meeting transcripts

What would you like to do today?

---

User: Upload a video
Agent: [calls request_video_upload]
Great! I've opened the video upload interface. Please select your meeting video and I'll transcribe it with speaker identification.

---

User: [uploads video]
Agent: [calls transcribe_uploaded_video]
✅ Transcription complete! [shows transcription]

Would you like me to:
1. Upload this to Pinecone for AI-powered search
2. Let you edit the transcription first

---

User: What meetings do I have?
Agent: [calls list_recent_meetings]
Here are your available meetings: [shows list]

Would you like me to summarize any of these meetings?
```

Remember: You're a helpful assistant focused on making meeting management effortless through natural conversation!"""

    def __init__(self, pinecone_manager, transcription_service):
        """
        Initialize the conversational agent.
        
        Args:
            pinecone_manager: Instance of PineconeManager for database access
            transcription_service: Instance of TranscriptionService for video processing
        """
        self.pinecone_mgr = pinecone_manager
        self.transcription_svc = transcription_service
        
        # Initialize tools
        initialize_tools(pinecone_manager)
        initialize_video_tools(transcription_service, pinecone_manager)
        
        # Combine all tools
        self.tools = [
            # Video processing tools
            request_video_upload,
            transcribe_uploaded_video,
            request_transcription_edit,
            update_transcription,
            upload_transcription_to_pinecone,
            cancel_video_workflow,
            # Meeting query tools
            search_meetings,
            get_meeting_metadata,
            list_recent_meetings
        ]
        
        # Create LLM with tool binding
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
        workflow = StateGraph(ConversationalAgentState)
        
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
    
    def _prepare_messages(self, state: ConversationalAgentState) -> ConversationalAgentState:
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
    
    def _call_agent(self, state: ConversationalAgentState) -> Dict[str, Any]:
        """
        Node 2: Call the LLM agent (may invoke tools).
        """
        if state.get("error"):
            return {}
        
        try:
            llm_messages = state["llm_messages"]
            response = self.llm.invoke(llm_messages)
            
            # Return the new message to be appended
            return {"llm_messages": [response]}
            
        except Exception as e:
            print(f"ERROR in _call_agent: {str(e)}")
            return {"error": f"Error calling agent: {str(e)}"}
    
    def _should_continue(self, state: ConversationalAgentState) -> str:
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
        Main entry point - generates a streaming response using the conversational agent.
        
        Args:
            message: The user's current message
            history: Conversation history in Gradio format [[user, bot], ...]
        
        Yields:
            Streaming response strings
        """
        # Initialize state
        initial_state: ConversationalAgentState = {
            "message": message,
            "history": history,
            "llm_messages": [],
            "response": "",
            "error": None
        }
        
        try:
            # Use stream to get intermediate events
            # This allows us to notify the user when tools are being called
            final_response = ""
            
            for event in self.graph.stream(initial_state):
                # Handle agent events
                if "agent" in event:
                    agent_update = event["agent"]
                    if "llm_messages" in agent_update:
                        last_msg = agent_update["llm_messages"][-1]
                        
                        # Check for tool calls
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                tool_name = tool_call.get("name", "")
                                if tool_name == "transcribe_uploaded_video":
                                    yield "🎬 Starting video transcription... (this may take a few minutes)\n"
                                elif tool_name == "upload_transcription_to_pinecone":
                                    yield "💾 Uploading to Pinecone...\n"
                                elif tool_name == "search_meetings":
                                    yield "🔍 Searching your meetings...\n"
                        
                        # Check for final response (AIMessage without tool calls)
                        elif isinstance(last_msg, AIMessage) and last_msg.content:
                            final_response = last_msg.content
                            yield final_response
                
                # Handle error events
                if "error" in event:
                    yield f"❌ Error: {event['error']}"
                    return

            # If we didn't get a final response in the stream (sometimes happens with complex graphs),
            # check if we have one buffered
            if not final_response:
                # This part is a bit tricky with stream, but usually the last agent step provides the response
                pass
                
        except Exception as e:
            import traceback
            print(f"Error in generate_response: {traceback.format_exc()}")
            yield f"Error generating response: {str(e)}"


# Alias for clarity
ConversationalAgent = ConversationalMeetingAgent
