import re
from typing import List, Dict, Any, Generator, TypedDict, Optional, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.config.settings import Config


class AgentState(TypedDict):
    """State for the RAG agent graph."""
    message: str                          # Current user query
    history: List[List[str]]              # Conversation history [[user, bot], ...]
    search_kwargs: Dict[str, Any]         # Retrieval parameters
    documents: List[Any]                  # Retrieved documents
    llm_messages: List[Any]               # LLM messages for streaming
    response: str                         # Generated response
    error: Optional[str]                  # Error message if any


class RagAgentLangGraph:
    """
    LangGraph-based RAG agent service.
    Uses a state graph with explicit nodes for analysis, retrieval, and generation.
    """
    
    def __init__(self, pinecone_manager):
        self.pinecone_mgr = pinecone_manager
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY,
            streaming=True
        )
        
        # Build the state graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Builds the LangGraph state graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze", self._analyze_query)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("generate", self._generate_response)
        
        # Define edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _get_retrieval_kwargs(self, query: str) -> Dict[str, Any]:
        """
        Determines dynamic retrieval parameters based on query intent.
        """
        query_lower = query.lower()
        
        # Check for meeting_id in query (e.g., "meeting_abc12345")
        meeting_id_match = re.search(r'meeting_([a-f0-9]{8})', query)
        meeting_id = meeting_id_match.group(0) if meeting_id_match else None
        
        # Determine optimal k and filters based on query type
        comprehensive_keywords = ["summarize", "summary", "all", "entire", "complete", "overview", "everything", "full"]
        is_comprehensive = any(keyword in query_lower for keyword in comprehensive_keywords)
        
        if meeting_id and is_comprehensive:
            # Specific meeting summary - retrieve ALL chunks from that meeting
            return {
                "k": 100,  # High k to ensure we get all chunks
                "filter": {"meeting_id": {"$eq": meeting_id}}
            }
        elif is_comprehensive:
            # General comprehensive question - retrieve many chunks
            return {"k": 20}
        else:
            # Specific question - semantic search with moderate k
            return {"k": 5}
    
    def _analyze_query(self, state: AgentState) -> AgentState:
        """
        Node 1: Analyze the query and determine retrieval strategy.
        """
        try:
            search_kwargs = self._get_retrieval_kwargs(state["message"])
            state["search_kwargs"] = search_kwargs
        except Exception as e:
            state["error"] = f"Error analyzing query: {str(e)}"
        
        return state
    
    def _retrieve_documents(self, state: AgentState) -> AgentState:
        """
        Node 2: Retrieve relevant documents from Pinecone.
        """
        if state.get("error"):
            return state  # Skip if there's already an error
        
        if not self.pinecone_mgr:
            state["error"] = "❌ Pinecone service is not available."
            return state
        
        try:
            retriever = self.pinecone_mgr.get_retriever(
                namespace="default",
                search_kwargs=state["search_kwargs"]
            )
            docs = retriever.invoke(state["message"])
            state["documents"] = docs
        except Exception as e:
            state["error"] = f"Error during retrieval: {str(e)}"
        
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """
        Node 3: Generate response using LLM.
        Note: This doesn't stream - streaming happens in generate_response method.
        """
        if state.get("error"):
            state["response"] = state["error"]
            return state
        
        # Prepare context
        docs = state.get("documents", [])
        context_str = "\n\n".join([d.page_content for d in docs]) if docs else "No relevant documents found."
        
        # Build system prompt
        system_prompt = """You are a helpful meeting assistant. Answer questions based on the provided meeting transcript excerpts.

Guidelines:
- Provide direct, concise answers
- Quote relevant parts when helpful
- If the context doesn't contain the answer, say so
- Don't repeat the user's question in your response"""
        
        llm_messages = [
            SystemMessage(content=system_prompt)
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
        
        # Add current query with context
        llm_messages.append(HumanMessage(content=f"Context from meeting transcripts:\n{context_str}"))
        llm_messages.append(HumanMessage(content=state["message"]))
        
        # Store messages for streaming (we'll use this in generate_response)
        state["llm_messages"] = llm_messages
        state["response"] = ""  # Will be filled during streaming
        
        return state
    
    def generate_response(self, message: str, history: List[List[str]]) -> Generator[str, None, None]:
        """
        Main entry point - generates a streaming response using the state graph.
        Maintains the same interface as the original RagAgentService.
        """
        # Initialize state
        initial_state: AgentState = {
            "message": message,
            "history": history,
            "search_kwargs": {},
            "documents": [],
            "llm_messages": [],
            "response": "",
            "error": None
        }
        
        try:
            # Run the graph through analyze and retrieve nodes
            final_state = self.graph.invoke(initial_state)
            
            # Check for errors
            if final_state.get("error"):
                yield final_state["error"]
                return
            
            # Stream the LLM response
            llm_messages = final_state.get("llm_messages", [])
            if not llm_messages:
                yield "Error: No messages to send to LLM"
                return
            
            full_response = ""
            for chunk in self.llm.stream(llm_messages):
                if chunk.content:
                    full_response += chunk.content
                    yield full_response
                    
        except Exception as e:
            yield f"Error generating response: {str(e)}"
