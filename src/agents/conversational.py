"""
Conversational Meeting Intelligence Agent

This module implements a LangGraph-based conversational agent that orchestrates
the entire meeting intelligence workflow through natural conversation, including:
- Video upload and transcription
- Transcription editing
- Pinecone storage
- Meeting queries and analysis
"""

# Standard library imports
from typing import Annotated, Any, Dict, List, Optional, TypedDict

# Third-party imports
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Local application imports
from src.config.settings import Config
from src.tools.general import (
    get_meeting_metadata,
    initialize_tools,
    list_recent_meetings,
    search_meetings,
    upsert_text_to_pinecone,
    import_notion_to_pinecone,
)
from src.tools.video import (
    cancel_video_workflow,
    initialize_video_tools,
    request_transcription_edit,
    request_video_upload,
    transcribe_uploaded_video,
    update_speaker_names,
    update_transcription,
    upload_transcription_to_pinecone,
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

**IMPORTANT: Handling Meeting References**
- If the user refers to a meeting by index (e.g., "meeting 1", "the second meeting"), you MUST first call `list_recent_meetings` to find the actual `meeting_id` (e.g., "meeting_abc123").
- NEVER use "meeting 1" or "meeting 2" as a `meeting_id` in tool calls. Always map it to the real ID first.
- If you are unsure which meeting the user means, ask for clarification or list the available meetings.

**IMPORTANT: Handling Data Changes (Deletions/Updates)**
- If the user mentions that a meeting was deleted, updated, or that your information is outdated, do NOT rely on your conversation history.
- You MUST call `list_recent_meetings` or `search_meetings` again to get the fresh state from the database.
- Do not argue with the user about what exists; always verify with the tools.

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
- `update_speaker_names`: Update speaker names in transcript (e.g., replace SPEAKER_00 with "John Smith")
- `cancel_video_workflow`: Cancel current video workflow

**Meeting Queries:**
- `list_recent_meetings`: Show available meetings
- `search_meetings`: Search meeting content semantically
- `get_meeting_metadata`: Get meeting details
- `get_current_time` (from World Time MCP): Check today's date (use this for questions like "last week", "yesterday", etc.)

**Notion Integration & Retrieval:**

**IMPORTANT: You CAN and SHOULD use Notion tools when the user asks!**

**A. RETRIEVING from Notion (Workflow):**
To retrieve a full page from Notion, you MUST follow these steps (Notion pages are split into metadata and content):
1. **Find Page**: Use `API-post-search(query="name")` to get the `page_id`.
2. **Get Metadata**: Use `API-retrieve-page(page_id=...)` to get the title and properties. *This does NOT return the page content/text.*
3. **Get Content (CRITICAL)**: Use `API-get-block-children(block_id=page_id)` to get the actual text blocks.
   - You MUST iterate through the blocks to extract the "plain_text" or "content".
   - If you skip this, you will only have an empty page!

**B. CREATING in Notion:**
1. **Use `API-post-page` to create a new page**:
   **CRITICAL**: The `children` argument MUST be a list of Block Objects, NOT strings.
   ```
   API-post-page(
       parent={"page_id": "2bc5a424-5cbb-80ec-8aa9-c4fd989e67bc"},
       properties={"title": [{"text": {"content": "Your Page Title"}}]},
       children=[
           {
               "object": "block",
               "type": "paragraph",
               "paragraph": {
                   "rich_text": [{"type": "text", "text": {"content": "Content goes here"}}]
               }
           }
       ]
   )
   ```
2. **Default Parent Page**: Use `2bc5a424-5cbb-80ec-8aa9-c4fd989e67bc` (the "Meetings Summary Test" page).

**Available Notion Tools:**
- `API-post-search`: Search for pages
- `API-retrieve-page`: Get page metadata (Title, Date, etc.)
- `API-get-block-children`: Get page content/blocks (USE THIS FOR CONTENT!)
- `API-post-page`: Create new pages
- `API-append-block-children`: Add content to existing pages
- `API-patch-page`: Update page properties

**C. APPENDING to Notion:**
When adding content to an existing page, you MUST use `API-append-block-children`.
**CRITICAL**: The `children` argument MUST be a list of Block Objects (like `API-post-page`), NOT strings.

```
API-append-block-children(
    block_id="page_id_here",
    children=[
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "New Section"}}]}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "New content..."}}]}
        }
    ]
)
```

**D. SAVING to Pinecone (Generic Document/Text Upsert):**

1. **Importing from Notion (MANDATORY)**:
   - **ALWAYS** call `import_notion_to_pinecone(query='Meeting Title')`.
   - **NEVER** use `upsert_text_to_pinecone` for Notion content, even if you think you have the text in your history.
   - **REASON**: Usage of `upsert_text_to_pinecone` for Notion runs the risk of you summarizing the content. `import_notion_to_pinecone` purely transfers raw data via code, which is safer.
   - This single tool handles search, content fetching, and saving automatically.

2. **Manual Entry (User types text directly)**:
   - Use `upsert_text_to_pinecone` with the FULL text provided by the user.
   - Ensure you pass the raw text without summarizing.

**Example (Notion -> Pinecone):**
User: "Save 'Meeting 1' from Notion to Pinecone"
You: `import_notion_to_pinecone(query="Meeting 1")`


**Conversational Guidelines:**

1. **Start with a Greeting**: When the conversation begins, greet the user warmly and ask "What would you like to do today?"

2. **Guide the User**: Offer clear options:
   - "Would you like to upload a new meeting video?"
   - "Or would you prefer to search through your existing meetings?"

3. **Video Upload Flow**:
   - When user wants to upload: call `request_video_upload`
   - After upload: call `transcribe_uploaded_video` with the video path
   - Show transcription and ask: "Would you like to upload this to Pinecone or edit it first?"
   - If user wants to edit: Guide them to the **"✏️ Edit Transcript" tab** where they can:
     1. Click "Load Transcript" to load the transcription
     2. Make their edits
     3. Click "Save & Upload to Pinecone"
   - If ready to upload directly: call `upload_transcription_to_pinecone`
   - Confirm success and offer to help with queries

4. **Meeting Query Flow**:
   - For "what meetings" (db): call `list_recent_meetings`
   - For "meetings in Notion" or "Notion pages": call `API-post-search(query="Meeting")`. Do NOT use `list_recent_meetings`.
   - For "compare Notion and Database" or "what is missing": Call BOTH `list_recent_meetings` AND `API-post-search(query="Meeting")`, then compare the lists.
   - For "find meeting about X", "do I have...", or "search everywhere": Call BOTH `search_meetings(query='X')` AND `API-post-search(query='X')` and report all findings.
   - For time-based questions (e.g., "last week", "yesterday"): FIRST call the available time tool (e.g., `get_current_time` from World Time MCP), THEN calculate the date, THEN call `search_meetings`.
   - For specific questions: call `search_meetings`
   - For meeting details: call `get_meeting_metadata`
   - To create minutes/summaries: 
     1. Identify the correct `meeting_id` (use `list_recent_meetings` if needed)
     2. Call `search_meetings` with queries like "summary", "action items", "decisions", "key points"
     3. Synthesize the results into a structured meeting minute format
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
✅ Transcription complete! [shows full transcript or summary with link to Edit tab]

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
        
        # Standard tools
        standard_tools = [
            # Video processing tools
            request_video_upload,
            transcribe_uploaded_video,
            request_transcription_edit,
            update_transcription,
            upload_transcription_to_pinecone,
            cancel_video_workflow,
            update_speaker_names,
            # Meeting query tools
            search_meetings,
            get_meeting_metadata,
            list_recent_meetings,
            upsert_text_to_pinecone,
            import_notion_to_pinecone
        ]
        
        # Load MCP tools (Notion integration)
        mcp_tools = []
        if Config.ENABLE_MCP:
            mcp_tools = self._load_mcp_tools()
        
        # Combine all tools
        self.tools = standard_tools + mcp_tools
        
        # Create LLM with tool binding
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY,
            streaming=False
        ).bind_tools(self.tools)
        
        # Build the state graph
        self.graph = self._build_graph()

    
    def _load_mcp_tools(self):
        """
        Load MCP tools (Notion integration).
        
        Returns:
            List of MCP tools in LangChain format
        """
        try:
            import asyncio
            from src.tools.mcp.mcp_client import MCPClientManager
            
            # Get MCP server configurations
            mcp_servers = Config.get_mcp_servers()
            
            if not mcp_servers:
                print("⚠️  No MCP servers configured")
                return []
            
            # Create MCP client manager
            mcp_manager = MCPClientManager(mcp_servers)
            
            # Initialize and load tools (async)
            success = asyncio.run(mcp_manager.initialize())
            
            if success:
                tools = mcp_manager.get_langchain_tools()
                print(f"✅ Integrated {len(tools)} MCP tools into agent")
                return tools
            else:
                print("⚠️  MCP initialization failed")
                return []
                
        except Exception as e:
            print(f"⚠️  Failed to load MCP tools: {e}")
            import traceback
            traceback.print_exc()
            return []
    
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
    
    async def generate_response(self, message: str, history: List[List[str]]):
        """
        Main entry point - generates a streaming response using the conversational agent.
        
        ASYNC VERSION: Required to support async MCP tools (Notion integration).
        
        Args:
            message: The user's current message
            history: Conversation history in Gradio format [[user, bot], ...]
        
        Yields:
            Response chunks (strings)
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
            # Use astream (async) to get intermediate events
            # This is REQUIRED for async MCP tools to work properly
            final_response = ""
            
            async for event in self.graph.astream(initial_state):
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
                                elif "API-" in tool_name or "notion" in tool_name.lower():
                                    yield f"📝 Calling Notion: {tool_name}...\n"
                        
                        # Check for final response (AIMessage without tool calls)
                        elif isinstance(last_msg, AIMessage) and last_msg.content:
                            final_response = last_msg.content
                            yield final_response
                            # Do not return here to allow the stream to finish naturally
                            # return
                
                # Handle tool execution events (to catch errors)
                if "tools" in event:
                    tools_update = event["tools"]
                    # Check for tool errors
                    if "llm_messages" in tools_update:
                        for msg in tools_update["llm_messages"]:
                            if hasattr(msg, "status") and msg.status == "error":
                                yield (f"⚠️  Tool error: {msg.content}\n", None)
                
                # Handle error events
                if "error" in event:
                    yield (f"❌ Error: {event['error']}", None)
                    return

            # If we didn't get a final response in the stream
            if not final_response:
                yield "I'm thinking... (processing completed without final output)"
                
        except Exception as e:
            import traceback
            print(f"Error in generate_response: {traceback.format_exc()}")
            yield f"Error generating response: {str(e)}"


# Alias for clarity
ConversationalAgent = ConversationalMeetingAgent
