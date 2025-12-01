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






#     def generate_response(self, message: str, history: List[List[str]]) -> Generator[List[ChatMessage], None, None]:
#         """
#         Generates a response using RAG, yielding a list of ChatMessages to support
#         rich UI with 'thinking' steps.
#         """
#         # 1. Prepare the chat messages list (History + New User Message)
#         # Handle both ChatMessage objects and dictionaries (Gradio 6.x standard format)
#         chat_messages = []
#         for msg in history:
#             if isinstance(msg, dict):
#                 chat_messages.append(ChatMessage(role=msg.get("role"), content=msg.get("content")))
#             elif isinstance(msg, ChatMessage):
#                 chat_messages.append(msg)
#             # Handle list/tuple format [user, bot] if necessary (older Gradio)
#             elif isinstance(msg, (list, tuple)) and len(msg) == 2:
#                 chat_messages.append(ChatMessage(role="user", content=msg[0]))
#                 chat_messages.append(ChatMessage(role="assistant", content=msg[1]))
                
#         chat_messages.append(ChatMessage(role="user", content=message))
        
#         if not self.pinecone_mgr:
#             chat_messages.append(ChatMessage(role="assistant", content="❌ Pinecone service is not available. Please check your API key configuration."))
#             yield chat_messages
#             return

#         # 2. Add the initial 'Thinking' message
#         """
#         thought_message = ChatMessage(
#             role="assistant",
#             content = "Processing your request...",  # ✅ Clean, no question repetition
#             # content=f"Analyzing request: '{message}'...",
#             metadata={
#                 "title": "🧠 Thinking Process",
#                 "log": "Initializing RAG pipeline...",
#                 "status": "pending"
#             }
#         )
#         chat_messages.append(thought_message)
#         yield chat_messages
#         """
#         # 3. Retrieval Step
#         search_kwargs = self._get_retrieval_kwargs(message)
#         k_value = search_kwargs.get("k", 5)
        
#         """# Update thought log
#         thought_message.metadata["log"] += f"\n🔍 Retrieval Strategy: Fetching top {k_value} segments..."
#         yield chat_messages"""
        
#         docs = []
#         try:
#             retriever = self.pinecone_mgr.get_retriever(
#                 namespace="default",
#                 search_kwargs=search_kwargs
#             )
#             docs = retriever.get_relevant_documents(message)
            
#             # if not docs:
#             #     thought_message.metadata["log"] += "\n⚠️ No relevant documents found."
#             # else:
#             #     thought_message.metadata["log"] += f"\n✅ Found {len(docs)} relevant segments."
                
#             yield chat_messages
                
#         except Exception as e:
#             # thought_message.metadata["log"] += f"\n❌ Retrieval Error: {str(e)}"
#             # thought_message.metadata["status"] = "done"
#             chat_messages.append(ChatMessage(role="assistant", content=f"Error during retrieval: {str(e)}"))
#             yield chat_messages
#             return

#         # 4. Generation Step
#         # thought_message.metadata["log"] += f"\n🧠 Generating response with {Config.MODEL_NAME}..."
#         yield chat_messages
        
#         # Prepare prompt context
#         context_str = "\n\n".join([d.page_content for d in docs])
        
#         # Convert history to LangChain format for the prompt (if needed) or just use messages
#         # We'll construct the messages for the LLM directly
#         from langchain.schema import SystemMessage, HumanMessage, AIMessage as LC_AIMessage
        
#         llm_messages = [
#             SystemMessage(content="You are a helpful meeting assistant. Use the provided meeting transcript excerpts to answer questions accurately and concisely.")
#         ]
        
#         # Add history to LLM messages
#         # We iterate over chat_messages which we know contains ChatMessage objects
#         # Skip the last one (current user message) as we add it with context below
#         # Also skip the thought messages (metadata present)
#         for msg in chat_messages[:-1]:
#             if msg.metadata: # Skip thought messages
#                 continue
                
#             if msg.role == "user":
#                 llm_messages.append(HumanMessage(content=msg.content))
#             elif msg.role == "assistant":
#                 llm_messages.append(LC_AIMessage(content=msg.content))
                
#         # Add current context and question
#         llm_messages.append(HumanMessage(content=f"Context:\n{context_str}\n\nQuestion: {message}"))
        
#         # Stream response - REPLACE the thinking message with the actual response
#         try:
#             full_response = ""
#             for chunk in self.llm.stream(llm_messages):
#                 if chunk.content:
#                     full_response += chunk.content
#                     final_response.content = full_response
#                     # UPDATE the thinking message content instead of adding a new one
#                     # thought_message.content = full_response
#                     yield chat_messages
            
#             # Mark thought as done and remove thinking metadata
#             # thought_message.metadata["status"] = "done"
#             # Remove the thinking UI elements to show clean response
#             # thought_message.metadata = {}
#             yield chat_messages
                        
#         # # Change from here |----->
#         # # Initialize final response message
#         final_response = ChatMessage(role="assistant", content="")
#         chat_messages.append(final_response)
        
#         # # Stream response
#         # try:
#         #     full_response = ""
#         #     for chunk in self.llm.stream(llm_messages):
#         #         if chunk.content:
#         #             full_response += chunk.content
#         #             final_response.content = full_response
#         #             yield chat_messages
            
#         #     # Mark thought as done
#         #     thought_message.metadata["status"] = "done"
#         #     thought_message.metadata["log"] += "\n✅ Generation complete."
#         #     yield chat_messages
#             # # Change to here <-----
            
#         except Exception as e:
#             # thought_message.metadata["status"] = "done"
#             # thought_message.metadata["log"] += f"\n❌ Generation Error: {str(e)}"
#             final_response.content += f"\n\nError generating response: {str(e)}"
#             yield chat_messages
#             return

# # Version without thinking UI
# # def generate_response(self, message: str, history: List[List[str]]) -> Generator[List[ChatMessage], None, None]:
# #     """
# #     Clean version without thinking UI - just returns the answer
# #     """
# #     # 1. Prepare the chat messages list from Gradio history format
# #     chat_messages = []
    
# #     # Convert Gradio history format: [ [user1, assistant1], [user2, assistant2], ... ]
# #     for user_msg, assistant_msg in history:
# #         if user_msg:
# #             chat_messages.append(ChatMessage(role="user", content=user_msg))
# #         if assistant_msg:
# #             chat_messages.append(ChatMessage(role="assistant", content=assistant_msg))
    
# #     # Add current user message
# #     chat_messages.append(ChatMessage(role="user", content=message))
    
# #     if not self.pinecone_mgr:
# #         error_msg = ChatMessage(role="assistant", content="❌ Pinecone service is not available.")
# #         chat_messages.append(error_msg)
# #         yield chat_messages
# #         return

# #     try:
# #         # Do retrieval
# #         search_kwargs = self._get_retrieval_kwargs(message)
# #         retriever = self.pinecone_mgr.get_retriever(
# #             namespace="default", 
# #             search_kwargs=search_kwargs
# #         )
# #         docs = retriever.get_relevant_documents(message)
        
# #         # Prepare context
# #         context_str = "\n\n".join([d.page_content for d in docs]) if docs else "No relevant documents found."
        
# #         # Prepare LLM messages
# #         from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        
# #         llm_messages = [
# #             SystemMessage(content="You are a helpful meeting assistant. Use the provided meeting transcript excerpts to answer questions accurately and concisely.")
# #         ]
        
# #         # Add conversation history
# #         for user_msg, assistant_msg in history:
# #             if user_msg:
# #                 llm_messages.append(HumanMessage(content=user_msg))
# #             if assistant_msg:
# #                 llm_messages.append(AIMessage(content=assistant_msg))
                
# #         # Add current context and question
# #         llm_messages.append(HumanMessage(content=f"Context:\n{context_str}\n\nQuestion: {message}"))
        
# #         # Create and stream the response
# #         response_message = ChatMessage(role="assistant", content="")
# #         chat_messages.append(response_message)
        
# #         full_response = ""
# #         for chunk in self.llm.stream(llm_messages):
# #             if chunk.content:
# #                 full_response += chunk.content
# #                 response_message.content = full_response
# #                 yield chat_messages
                
# #     except Exception as e:
# #         error_msg = ChatMessage(role="assistant", content=f"❌ Error: {str(e)}")
# #         chat_messages.append(error_msg)
# #         yield chat_messages

