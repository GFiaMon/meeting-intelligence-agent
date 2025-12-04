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
from langchain.tools import tool
from langchain_core.documents import Document

from src.retrievers.pipeline import process_transcript_to_documents
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


# Export all tools for easy import
__all__ = [
    "initialize_tools",
    "search_meetings",
    "get_meeting_metadata",
    "list_recent_meetings",
    "upsert_text_to_pinecone"
]


@tool
def upsert_text_to_pinecone(text: str, title: str, source: str = "Manual Entry", date: str = None) -> str:
    """
    Upsert any text content (e.g., Notion pages, manual notes) to Pinecone.
    
    Use this tool when the user wants to save a Notion page, meeting notes, or any other text
    that is NOT a video transcription.
    
    Args:
        text: The content to save
        title: Title of the document/meeting
        source: Source of the content (e.g., "Notion", "Manual Entry")
        date: Date of the content (YYYY-MM-DD). Defaults to today.
    
    Returns:
        Success message with the generated meeting_id
    """
    if not _pinecone_manager:
        return "Error: Pinecone service is not initialized."
        
    try:
        # Generate ID and defaults
        meeting_id = f"doc_{uuid.uuid4().hex[:8]}"
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        # Create comprehensive metadata with consistent field names
        meeting_metadata = {
            "meeting_id": meeting_id,
            "meeting_date": date,  # ✅ Fixed: was "date"
            "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
            "source": source,
            "meeting_title": title,  # ✅ Fixed: was "title"
            "summary": f"Imported from {source}",  # ✅ Added summary
            "source_file": f"{source.lower()}_upload",
            "transcription_model": "text_import",
            "language": "en"
        }
        
        # Process text into documents (using fallback chunking since no speaker data)
        docs = process_transcript_to_documents(
            transcript_text=text,
            speaker_data=None,
            meeting_id=meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        # Upsert to Pinecone
        _pinecone_manager.upsert_documents(docs, namespace=Config.PINECONE_NAMESPACE)
        
        return f"✅ Successfully saved '{title}' to Pinecone (ID: {meeting_id})"
        
    except Exception as e:
        return f"❌ Error saving to Pinecone: {str(e)}"
