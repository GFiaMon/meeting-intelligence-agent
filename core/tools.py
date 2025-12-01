"""
LangChain Tools for Meeting Intelligence Agent

This module defines tools that can be used by LangChain agents to interact
with meeting transcripts stored in Pinecone.

Tools follow the official @tool decorator pattern from LangChain.
Reference: https://docs.langchain.com/oss/python/langchain/tools#create-tools
"""

from typing import List, Dict, Any, Optional
from langchain.tools import tool
from langchain_core.documents import Document


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
        meeting_id: Optional meeting ID to search within a specific meeting (e.g., "meeting_abc12345")
    
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
            namespace="default",
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
            date = metadata.get("date", "unknown")
            chunk_index = metadata.get("chunk_index", "?")
            
            result_parts.append(
                f"\n--- Segment {i} ---\n"
                f"Meeting: {meeting_id} (Date: {date})\n"
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
            namespace="default",
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
            f"- Date: {metadata.get('date', 'N/A')}",
            f"- Title: {metadata.get('title', 'N/A')}",
            f"- Source: {metadata.get('source', 'N/A')}",
            f"- Source File: {metadata.get('source_file', 'N/A')}",
            f"- Language: {metadata.get('language', 'N/A')}",
            f"- Transcription Model: {metadata.get('transcription_model', 'N/A')}",
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
            namespace="default",
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
                    "date": metadata.get("date", "N/A"),
                    "title": metadata.get("title", "N/A"),
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
    "list_recent_meetings"
]
