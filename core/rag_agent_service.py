import os
from openai import OpenAI
from typing import List, Dict, Any, Iterator

from config import Config


# --- API Configuration ---

OPENAI_API_KEY = Config.OPENAI_API_KEY
MODEL_NAME = Config.MODEL_NAME

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

def rag_logic(
    client: OpenAI,
    pinecone_mgr: Any, # Expecting PineconeManager instance
    message: str,
    history: List[List[str]]
) -> Iterator[str | Dict[str, Any]]:
    """
    Core RAG and LLM generation logic. It handles retrieval, prompt building,
    and streaming the LLM response.

    Yields thought logs (dict) for UI updates and then the final streaming text (str).
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
        # Use the injected PineconeManager to query
        search_results = pinecone_mgr.query_index(query=message, top_k=3, namespace="default")
        
        if search_results and "matches" in search_results:
            
            for match in search_results["matches"][:3]: 
                if "metadata" in match:
                    # Extract meeting segment information
                    text = match["metadata"].get("text", "")[:500] 
                    meeting_id = match["metadata"].get("meeting_id", "Unknown")
                    speaker = match["metadata"].get("speaker", "N/A")
                    
                    relevant_content += (
                        f"\n\n--- Source: Meeting {meeting_id} (Speaker {speaker}) ---\n"
                        f"{text}"
                    )
            
            yield {
                "title": "✅ Retrieval Complete",
                "log": f"Found {len(search_results['matches'])} relevant meeting segments.",
                "status": "done"
            }
            
        else:
            yield {
                "title": "⚠️ No Content Found",
                "log": "No relevant meeting transcripts were retrieved.",
                "status": "done"
            }
    except Exception as e:
        yield {
            "title": "❌ Retrieval Failed",
            "log": f"Storage error during search: {str(e)}",
            "status": "done"
        }
        return

    # 3. Prepare context-aware prompt
    system_prompt = f"""You are a helpful meeting assistant. Use the provided meeting transcripts to answer questions accurately and concisely. If no relevant meetings are provided, inform the user you could not find a source, then answer based on general knowledge if possible.

Available meeting context:
{relevant_content if relevant_content else "No meeting context available."}"""

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
            
            # Final yield to indicate success
            yield {
                "title": "✅ Generation Complete",
                "log": "Response streamed successfully.",
                "status": "final"
            }
            
        except Exception as e:
            yield f"API error during generation: {str(e)}"
    else:
        yield "OpenAI client not available. Please check your API key."