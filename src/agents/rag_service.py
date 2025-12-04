import re
from typing import List, Dict, Any, Generator, Union

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config.settings import Config

class RagAgentService:
    """
    Service for handling RAG-based chatbot interactions.
    Encapsulates retrieval logic, LLM generation, and history management.
    """
    
    def __init__(self, pinecone_manager):
        self.pinecone_mgr = pinecone_manager
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY,
            streaming=True
        )
        
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

    def generate_response(self, message: str, history: List[List[str]]) -> Generator[str, None, None]:
        """
        Generates a streaming response using RAG.
        Returns a generator that yields strings (not ChatMessage objects).
        """
        if not self.pinecone_mgr:
            yield "❌ Pinecone service is not available."
            return

        # Retrieval Step
        search_kwargs = self._get_retrieval_kwargs(message)
        
        docs = []
        try:
            retriever = self.pinecone_mgr.get_retriever(
                namespace="default",
                search_kwargs=search_kwargs
            )
            docs = retriever.invoke(message)
        except Exception as e:
            yield f"Error during retrieval: {str(e)}"
            return

        # Prepare context
        context_str = "\n\n".join([d.page_content for d in docs]) if docs else "No relevant documents found."
        
        # Build the system prompt with better instructions
        system_prompt = """You are a helpful meeting assistant. Answer questions based on the provided meeting transcript excerpts.
        
Guidelines:
- Provide direct, concise answers
- Quote relevant parts when helpful
- If the context doesn't contain the answer, say so
- Don't repeat the user's question in your response"""
        
        llm_messages = [
            SystemMessage(content=system_prompt)
        ]
        
        # Add conversation history
        for user_msg, assistant_msg in history:
            if user_msg:
                llm_messages.append(HumanMessage(content=user_msg))
            if assistant_msg:
                llm_messages.append(AIMessage(content=assistant_msg))
        
        # Add current query with context - DON'T repeat the question
        llm_messages.append(HumanMessage(content=f"Context from meeting transcripts:\n{context_str}"))
        llm_messages.append(HumanMessage(content=message))
        
        # Stream response
        try:
            full_response = ""
            for chunk in self.llm.stream(llm_messages):
                if chunk.content:
                    full_response += chunk.content
                    yield full_response  # Yield the accumulated response
            
        except Exception as e:
            yield f"Error generating response: {str(e)}"