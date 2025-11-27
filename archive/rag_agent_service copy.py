import os
from openai import OpenAI
from typing import List, Dict, Any, Iterator
from dotenv import load_dotenv

# Load environment variables just in case this service is run independently
load_dotenv()

# Placeholder for StorageService type hint (assuming a class named StorageService exists)
# In a real setup, you would import StorageService from core.storage_service
class StorageService:
    def search_transcripts(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Placeholder for the actual Pinecone search method."""
        raise NotImplementedError("StorageService must be injected.")


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME = "gpt-3.5-turbo"

def initialize_openai_client() -> OpenAI | None:
    """Initializes and returns the OpenAI client."""
    if OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            print("✅ OpenAI client initialized for RAG Agent.")
            return client
        except Exception as e:
            print(f"❌ OpenAI client initialization error in RAG Agent: {e}")
            return None
    return None


def chat_logic(
    client: OpenAI,
    storage_svc: Any, # Using Any for simplicity, but should be StorageService
    message: str,
    history: List[List[str]]
) -> Iterator[str | Dict[str, Any]]:
    """
    Core RAG and LLM generation logic. It handles retrieval, prompt building,
    and streaming the LLM response.

    Yields thought logs (dict) and then the final streaming text (str).
    """
    
    # 1. Yield Initial Search Thought
    yield {
        "title": "🔍 Searching Meetings",
        "log": f"Querying Pinecone for: '{message}'...",
        "status": "pending"
    }
    
    # 2. Search Pinecone for relevant meeting content
    relevant_content = ""
    try:
        search_results = storage_svc.search_transcripts(message, top_k=3)
        
        if search_results and "matches" in search_results:
            
            # Extract relevant content from search results
            for match in search_results["matches"][:3]: # Top 3 results
                if "metadata" in match:
                    text = match["metadata"].get("text", "")[:500] 
                    meeting_id = match["metadata"].get("meeting_id", "Unknown")
                    relevant_content += f"\n\n--- Meeting {meeting_id} (Score: {match.get('score', 'N/A'):.2f}) ---\n{text}"
            
            # Yield Search Done Thought
            yield {
                "title": "✅ Search Complete",
                "log": f"Found {len(search_results['matches'])} relevant meeting segments.",
                "status": "done"
            }
            
        else:
            yield {
                "title": "⚠️ No Content Found",
                "log": "No relevant meeting transcripts were retrieved from Pinecone.",
                "status": "done"
            }
    except Exception as e:
        yield {
            "title": "❌ Search Failed",
            "log": f"Storage error during search: {str(e)}",
            "status": "done"
        }
        return

    # 3. Prepare context-aware prompt
    system_prompt = f"""You are a helpful meeting assistant. Use the provided meeting transcripts to answer questions accurately and concisely. Do not mention the context if none was provided.

Available meeting context:
{relevant_content if relevant_content else "No relevant meetings found."}"""

    user_prompt = f"Question: {message}"

    # 4. Prepare messages for OpenAI
    openai_messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for user_msg, assistant_msg in history:
        if user_msg:
            openai_messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            openai_messages.append({"role": "assistant", "content": assistant_msg})
            
    openai_messages.append({"role": "user", "content": user_prompt})

    # 5. Yield Generation Thought
    yield {
        "title": "🧠 Generating Response",
        "log": f"Using {MODEL_NAME} with context...",
        "status": "pending"
    }
    
    # 6. Stream the LLM response
    if client:
        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=openai_messages,
                stream=True,
            )
            
            # Stream text chunks directly
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content # Yields the raw text chunk
            
        except Exception as e:
            yield f"API error during generation: {str(e)}"
    else:
        yield "OpenAI client not available. Please check your API key."

    # Yield completion signal (handled by the caller)
    return