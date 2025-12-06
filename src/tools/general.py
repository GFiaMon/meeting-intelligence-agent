"""
LangChain Tools for Meeting Intelligence Agent

This module defines tools that can be used by LangChain agents to interact
with meeting transcripts stored in Pinecone.

Tools follow the official @tool decorator pattern from LangChain.
Reference: https://docs.langchain.com/oss/python/langchain/tools#create-tools
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import requests
from langchain.tools import tool
from langchain_core.documents import Document

from src.retrievers.pipeline import process_transcript_to_documents
from src.processing.metadata_extractor import MetadataExtractor
from src.config.settings import Config

# Global reference to PineconeManager (will be set during initialization)
_pinecone_manager = None


def initialize_tools(pinecone_manager):
    """
    Initialize tools with a PineconeManager instance.
    
    Args:
        pinecone_manager: Instance of PineconeManager for database access
    """
    global _pinecone_manager
    _pinecone_manager = pinecone_manager


@tool
def search_meetings(query: str, max_results: int = 5, meeting_id: Optional[str] = None) -> str:
    """
    Search meeting transcripts for relevant information using semantic search.
    
    Use this tool when you need to find specific information across meeting transcripts.
    The search uses AI-powered semantic matching to find the most relevant segments.
    
    Args:
        query: The search query or question to find relevant meeting content
        max_results: Maximum number of results to return (default: 5)
        meeting_id: Optional meeting ID to search within a specific meeting (e.g., "meeting_abc12345"). DO NOT use indices like "1" or "2".
    
    Returns:
        A formatted string containing the most relevant meeting transcript segments
        
    Example:
        search_meetings("What were the action items?", max_results=3)
        search_meetings("budget discussion", meeting_id="meeting_abc12345")
    """
    if not _pinecone_manager:
        return "Error: Pinecone service is not initialized. Cannot search meetings."
    
    try:
        # Build search kwargs
        search_kwargs = {"k": max_results}
        
        # Add meeting_id filter if provided
        if meeting_id:
            search_kwargs["filter"] = {"meeting_id": {"$eq": meeting_id}}
        
        # Get retriever and perform search
        retriever = _pinecone_manager.get_retriever(
            namespace=Config.PINECONE_NAMESPACE,
            search_kwargs=search_kwargs
        )
        
        docs = retriever.invoke(query)
        
        if not docs:
            return "No relevant meeting segments found for your query."
        
        # Format results
        result_parts = [f"Found {len(docs)} relevant meeting segments:\n"]
        
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            meeting_id = metadata.get("meeting_id", "unknown")
            meeting_date = metadata.get("meeting_date", "unknown")  # ✅ Fixed: was "date"
            chunk_index = metadata.get("chunk_index", "?")
            
            result_parts.append(
                f"\n--- Segment {i} ---\n"
                f"Meeting: {meeting_id} (Date: {meeting_date})\n"
                f"Chunk: {chunk_index}\n"
                f"Content:\n{doc.page_content}\n"
            )
        
        return "".join(result_parts)
        
    except Exception as e:
        return f"Error searching meetings: {str(e)}"


@tool
def get_meeting_metadata(meeting_id: str) -> str:
    """
    Retrieve metadata and summary information for a specific meeting.
    
    Use this tool when you need to get details about a specific meeting,
    such as date, title, participants, or other metadata.
    
    Args:
        meeting_id: The unique identifier for the meeting (e.g., "meeting_abc12345")
    
    Returns:
        A formatted string containing the meeting's metadata
        
    Example:
        get_meeting_metadata("meeting_abc12345")
    """
    if not _pinecone_manager:
        return "Error: Pinecone service is not initialized. Cannot retrieve metadata."
    
    try:
        # Search for any document from this meeting to get metadata
        retriever = _pinecone_manager.get_retriever(
            namespace=Config.PINECONE_NAMESPACE,
            search_kwargs={
                "k": 1,
                "filter": {"meeting_id": {"$eq": meeting_id}}
            }
        )
        
        # Use a generic query to get any chunk from this meeting
        docs = retriever.invoke("meeting content")
        
        if not docs:
            return f"No meeting found with ID: {meeting_id}"
        
        # Extract metadata from the first document
        metadata = docs[0].metadata
        
        result_parts = [
            f"Meeting Information for {meeting_id}:\n",
            f"- Date: {metadata.get('meeting_date', 'N/A')}",  # ✅ Fixed: was 'date'
            f"- Title: {metadata.get('meeting_title', 'N/A')}",  # ✅ Fixed: was 'title'
            f"- Summary: {metadata.get('summary', 'N/A')}",  # ✅ Added summary
            f"- Source: {metadata.get('source', 'N/A')}",
            f"- Source File: {metadata.get('source_file', 'N/A')}",
            f"- Language: {metadata.get('language', 'N/A')}",
            f"- Transcription Model: {metadata.get('transcription_model', 'N/A')}",
            f"- Duration: {metadata.get('meeting_duration', 'N/A')}",  # ✅ Added duration
        ]
        
        return "\n".join(result_parts)
        
    except Exception as e:
        return f"Error retrieving meeting metadata: {str(e)}"


@tool
def list_recent_meetings(limit: int = 10) -> str:
    """
    Get a list of recent meetings stored in the system.
    
    Use this tool when you need to see what meetings are available,
    or to help the user understand what they can ask about.
    
    Args:
        limit: Maximum number of meetings to return (default: 10)
    
    Returns:
        A formatted string listing recent meetings with their IDs and dates
        
    Example:
        list_recent_meetings(limit=5)
    """
    if not _pinecone_manager:
        return "Error: Pinecone service is not initialized. Cannot list meetings."
    
    try:
        # Get retriever with high k to fetch many documents
        retriever = _pinecone_manager.get_retriever(
            namespace=Config.PINECONE_NAMESPACE,
            search_kwargs={"k": 100}  # Fetch many to find unique meetings
        )
        
        # Use a generic query to get documents
        docs = retriever.invoke("meeting")
        
        if not docs:
            return "No meetings found in the system."
        
        # Extract unique meetings
        meetings_dict = {}
        for doc in docs:
            metadata = doc.metadata
            meeting_id = metadata.get("meeting_id")
            
            if meeting_id and meeting_id not in meetings_dict:
                meetings_dict[meeting_id] = {
                    "date": metadata.get("meeting_date", "N/A"),  # ✅ Fixed: was "date"
                    "title": metadata.get("meeting_title", "N/A"),  # ✅ Fixed: was "title"
                    "source_file": metadata.get("source_file", "N/A")
                }
            
            # Stop if we've found enough unique meetings
            if len(meetings_dict) >= limit:
                break
        
        if not meetings_dict:
            return "No meetings found in the system."
        
        # Format results
        result_parts = [f"Found {len(meetings_dict)} recent meetings:\n"]
        
        for i, (meeting_id, info) in enumerate(meetings_dict.items(), 1):
            result_parts.append(
                f"\n{i}. {meeting_id}\n"
                f"   Date: {info['date']}\n"
                f"   Title: {info['title']}\n"
                f"   Source: {info['source_file']}"
            )
        
        return "\n".join(result_parts)
        
    except Exception as e:
        return f"Error listing meetings: {str(e)}"


@tool
def get_current_time() -> str:
    """
    Get the current date and time.
    
    Use this tool when you need to answer questions about relative time 
    (e.g., "what happened yesterday?", "meetings from last week?").
    
    Returns:
        Current date and time in YYYY-MM-DD HH:MM format
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@tool
def import_notion_to_pinecone(query: str) -> str:
    """
    Directly import a Notion page to Pinecone by name.
    
    Use this tool when the user wants to Import/Save/Upload a Notion page.
    This tool handles the entire process (Search -> Fetch Content -> Upsert) automatically
    to ensure NO data is lost or summarized.
    
    Args:
        query: The name of the Notion page to find (e.g., "Meeting 1").
        
    Returns:
        Status message indicating success or failure.
    """
    if not Config.NOTION_TOKEN:
        return "❌ Error: NOTION_TOKEN not set in configuration."

    
    headers = {
        "Authorization": f"Bearer {Config.NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        # 1. Search for the page
        print(f"🔍 Searching Notion for: {query}...")
        search_url = "https://api.notion.com/v1/search"
        search_payload = {
            "query": query,
            "filter": {"value": "page", "property": "object"},
            "page_size": 1
        }
        response = requests.post(search_url, headers=headers, json=search_payload)
        
        if response.status_code != 200:
            return f"❌ Notion Search Error: {response.text}"
            
        results = response.json().get("results", [])
        if not results:
            return f"❌ No Notion page found matching '{query}'."
            
        page = results[0]
        page_id = page["id"]
        
        # Extract title safely
        props = page.get("properties", {})
        title_prop = next((v for k, v in props.items() if v["id"] == "title"), None)
        title = "Untitled"
        if title_prop and title_prop.get("title"):
             title = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])])
             
        print(f"📄 Found Page: '{title}' ({page_id})")

        # 2. Get Block Children (Full Content)
        # We handle pagination to get ALL content
        all_text = []
        cursor = None
        has_more = True
        
        while has_more:
            blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
                
            resp = requests.get(blocks_url, headers=headers, params=params)
            if resp.status_code != 200:
                return f"❌ Error fetching blocks: {resp.text}"
                
            data = resp.json()
            blocks = data.get("results", [])
            
            for block in blocks:
                b_type = block.get("type")
                if b_type and block.get(b_type) and "rich_text" in block[b_type]:
                    rich_text = block[b_type]["rich_text"]
                    plain_text = "".join([t.get("plain_text", "") for t in rich_text])
                    if plain_text:
                        all_text.append(plain_text)
            
            has_more = data.get("has_more", False)
            cursor = data.get("next_cursor")

        full_content = "\n\n".join(all_text)
        
        if not full_content.strip():
            return f"⚠️ Page '{title}' found but appears empty or has no text blocks."

        # 3. Upsert to Pinecone (using the existing local function)
        # This will trigger the MetadataExtractor automatically
        return upsert_text_to_pinecone(text=full_content, title=title, source="Notion")

    except Exception as e:
        return f"❌ Import failed: {str(e)}"


# Export all tools for easy import
__all__ = [
    "initialize_tools",
    "search_meetings",
    "get_meeting_metadata",
    "list_recent_meetings",
    "upsert_text_to_pinecone",
    "import_notion_to_pinecone",
    "get_current_time"
]


@tool
def upsert_text_to_pinecone(text: str, title: str, source: str = "Manual Entry", date: str = None) -> str:
    """
    Upsert any text content (e.g., Notion pages, manual notes) to Pinecone.
    
    Automatically extracts metadata (summary, date, speakers) from the text.
    Use this tool when retrieving full content from Notion or other sources.
    
    Args:
        text: The FULL content to save (do not summarize!)
        title: Title of the document/meeting
        source: Source of the content (e.g., "Notion", "Manual Entry")
        date: Optional date override (YYYY-MM-DD). If not provided, AI extracts it from text or uses today.
    
    Returns:
        Success message with the generated meeting_id
    """
    if not _pinecone_manager:
        return "Error: Pinecone service is not initialized."
        
    try:
        
        # 1. Extract intelligent metadata
        print(f"🔍 Extracting metadata for '{title}'...")
        extractor = MetadataExtractor()
        extracted = extractor.extract_metadata(text)
        
        # 2. Resolve final metadata values
        final_summary = extracted.get("summary") or f"Imported from {source}"
        
        # Date logic: Argument > Extracted > Today
        if date:
            final_date = date
        elif extracted.get("meeting_date"):
            final_date = extracted.get("meeting_date")
        else:
            final_date = datetime.now().strftime("%Y-%m-%d")
            
        speaker_mapping = extracted.get("speaker_mapping", {})
            
        # 3. Apply speaker mapping to text (improves searchability)
        # Replaces "SPEAKER_00" -> "Name" directly in the text content
        processed_text = extractor.apply_speaker_mapping(text, speaker_mapping)
        
        # 4. Generate ID and prepare metadata
        meeting_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        meeting_metadata = {
            "meeting_id": meeting_id,
            "meeting_date": final_date,
            "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
            "source": source,
            "meeting_title": title,
            "summary": final_summary,
            "source_file": f"{source.lower()}_upload",
            "transcription_model": "text_import",
            "language": "en",
            "speaker_mapping": speaker_mapping
        }
        
        # 5. Process text into documents
        docs = process_transcript_to_documents(
            transcript_text=processed_text,
            speaker_data=None, # Uses fallback chunking
            meeting_id=meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        # 6. Upsert to Pinecone
        _pinecone_manager.upsert_documents(docs, namespace=Config.PINECONE_NAMESPACE)
        
        return (f"✅ Successfully saved '{title}' to Pinecone (ID: {meeting_id})\n"
                f"   - Date: {final_date}\n"
                f"   - Extracted Speakers: {', '.join(speaker_mapping.values()) if speaker_mapping else 'None'}")
        
    except Exception as e:
        return f"❌ Error saving to Pinecone: {str(e)}"
