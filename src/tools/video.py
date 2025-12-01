"""
Video Processing Tools for Conversational Meeting Intelligence Agent

This module defines LangChain tools that enable the agent to handle video upload,
transcription, editing, and storage workflows through conversational interactions.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from langchain.tools import tool

from src.processing.transcription import TranscriptionService
from src.retrievers.pinecone import PineconeManager
from src.retrievers.pipeline import process_transcript_to_documents


# Global references (will be set during initialization)
_transcription_service = None
_pinecone_manager = None
_video_state = {
    "uploaded_video_path": None,
    "transcription_text": None,
    "transcription_segments": None,
    "timing_info": None,
    "show_video_upload": False,
    "show_transcription_editor": False,
    "transcription_in_progress": False
}


def initialize_video_tools(transcription_service: TranscriptionService, pinecone_manager: PineconeManager):
    """
    Initialize video tools with required services.
    
    Args:
        transcription_service: Instance of TranscriptionService for video processing
        pinecone_manager: Instance of PineconeManager for database access
    """
    global _transcription_service, _pinecone_manager
    _transcription_service = transcription_service
    _pinecone_manager = pinecone_manager


def get_video_state() -> Dict[str, Any]:
    """Get current video processing state for UI updates."""
    return _video_state


def reset_video_state():
    """Reset video state after workflow completion."""
    global _video_state
    _video_state = {
        "uploaded_video_path": None,
        "transcription_text": None,
        "transcription_segments": None,
        "timing_info": None,
        "show_video_upload": False,
        "show_transcription_editor": False,
        "transcription_in_progress": False
    }


@tool
def request_video_upload() -> str:
    """
    Request the user to upload a video file for transcription.
    
    Use this tool when the user wants to upload a video or start the transcription workflow.
    This will show the video upload interface to the user.
    
    Returns:
        A message indicating the video upload interface is ready
        
    Example:
        User: "I want to upload a video"
        Agent: calls request_video_upload() -> shows video upload UI
    """
    global _video_state
    _video_state["show_video_upload"] = True
    _video_state["show_transcription_editor"] = False
    
    return "✅ Video upload interface is now ready. Please upload your video file and I'll transcribe it for you."


@tool
def transcribe_uploaded_video(video_path: str) -> str:
    """
    Transcribe an uploaded video file with speaker diarization.
    
    This tool processes the video through the transcription pipeline and returns
    the formatted transcription with speaker labels and timestamps.
    
    NOTE: The video_path should be extracted from the user's message if they mention
    uploading a video. Look for patterns like "[VIDEO_PATH: /path/to/video.mp4]" in the message.
    
    Args:
        video_path: Path to the uploaded video file
    
    Returns:
        Formatted transcription text with speaker labels and metadata
        
    Example:
        transcribe_uploaded_video("/path/to/video.mp4")
    """
    if not _transcription_service:
        return "❌ Error: Transcription service is not initialized."
    
    # Extract video path if it's embedded in brackets
    import re
    if "[VIDEO_PATH:" in video_path:
        match = re.search(r'\[VIDEO_PATH:\s*([^\]]+)\]', video_path)
        if match:
            video_path = match.group(1).strip()
    
    # Also extract from "Please transcribe my uploaded video: /path/to/video.mp4"
    if "Please transcribe" in video_path and ":" in video_path:
        video_path = video_path.split(":")[-1].strip()
    
    if not os.path.exists(video_path):
        return f"❌ Error: Video file not found"
    
    global _video_state
    _video_state["transcription_in_progress"] = True
    _video_state["uploaded_video_path"] = video_path
    
    # Get just the filename for display
    filename = os.path.basename(video_path)
    
    try:
        # Provide initial progress message
        progress_msg = f"""🎬 **Transcribing: {filename}**

**Processing Pipeline:**
1. ⏳ Loading audio from video...
2. ⏳ Transcribing with WhisperX...
3. ⏳ Aligning word-level timestamps...
4. ⏳ Identifying speakers...
5. ⏳ Assigning speakers to text...

⏱️ This may take a few minutes depending on video length. Please wait..."""
        
        # Process the video (progress updates handled internally by TranscriptionService)
        result = _transcription_service.transcribe_video(video_path)
        
        if not result.get("success", False):
            _video_state["transcription_in_progress"] = False
            return f"❌ Transcription failed: {result.get('error', 'Unknown error')}"
        
        # Store results in state
        _video_state["transcription_text"] = result["transcription"]
        _video_state["transcription_segments"] = result["raw_data"]["segments"]
        _video_state["timing_info"] = result["timing_info"]
        _video_state["transcription_in_progress"] = False
        _video_state["show_video_upload"] = False
        
        # Extract key statistics
        speakers_count = result.get("speakers_count", 0)
        processing_time = result.get("processing_time", 0)
        
        # Return formatted transcription with summary (hide temp path)
        return f"""✅ **Transcription Complete!**

**File:** {filename}
**Processing Time:** {processing_time:.1f}s
**Speakers Identified:** {speakers_count}

---

{result["transcription"]}

---

**What would you like to do next?**
1. 💾 Upload this transcription to Pinecone for AI-powered search
2. ✏️ Edit the transcription before uploading
3. ❌ Cancel and start over

Just let me know!"""
        
    except Exception as e:
        _video_state["transcription_in_progress"] = False
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in transcribe_uploaded_video: {error_details}")
        return f"❌ Error during transcription: {str(e)}"


@tool
def request_transcription_edit() -> str:
    """
    Allow the user to manually edit the transcription text.
    
    Use this tool when the user wants to make corrections or modifications
    to the transcription before uploading to Pinecone.
    
    Returns:
        A message indicating the transcription editor is ready
        
    Example:
        User: "I want to edit the transcription"
        Agent: calls request_transcription_edit() -> shows editable textbox
    """
    global _video_state
    
    if not _video_state["transcription_text"]:
        return "❌ No transcription available to edit. Please transcribe a video first."
    
    _video_state["show_transcription_editor"] = True
    
    return "✅ Transcription editor is now ready. You can make any changes to the text, then let me know when you're done."


@tool
def update_transcription(edited_text: str) -> str:
    """
    Update the transcription with user's edits.
    
    Args:
        edited_text: The edited transcription text from the user
    
    Returns:
        Confirmation message
        
    Example:
        update_transcription("Corrected transcription text...")
    """
    global _video_state
    
    if not edited_text:
        return "❌ No edited text provided."
    
    _video_state["transcription_text"] = edited_text
    _video_state["show_transcription_editor"] = False
    
    return "✅ Transcription updated successfully! Would you like to upload it to Pinecone now?"


@tool
def upload_transcription_to_pinecone() -> str:
    """
    Upload the current transcription to Pinecone vector database for AI-powered search.
    
    This tool creates a unique meeting ID, processes the transcription into chunks,
    and stores them in Pinecone with metadata for semantic search.
    
    Returns:
        Status message with meeting ID and upload details
        
    Example:
        User: "Upload it to Pinecone"
        Agent: calls upload_transcription_to_pinecone() -> stores in database
    """
    if not _pinecone_manager:
        return "❌ Error: Pinecone service is not initialized."
    
    global _video_state
    
    if not _video_state["transcription_text"]:
        return "❌ No transcription available to upload. Please transcribe a video first."
    
    try:
        # Generate unique meeting ID
        meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        meeting_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create metadata
        video_filename = os.path.basename(_video_state["uploaded_video_path"]) if _video_state["uploaded_video_path"] else "unknown"
        
        meeting_metadata = {
            "meeting_id": meeting_id,
            "date": meeting_date,
            "source": "video_upload",
            "title": f"Meeting {meeting_date}",
            "source_file": video_filename,
            "transcription_model": "whisperx-large-v2",
            "language": "en"  # Could be extracted from timing_info if available
        }
        
        # Process transcription into documents
        segments = _video_state.get("transcription_segments", [])
        docs = process_transcript_to_documents(
            _video_state["transcription_text"],
            segments,
            meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        # Upload to Pinecone
        _pinecone_manager.upsert_documents(docs, namespace="default")
        
        # Calculate statistics
        avg_chunk_size = sum(d.metadata['char_count'] for d in docs) // len(docs) if docs else 0
        
        # Reset state after successful upload
        reset_video_state()
        
        return f"""✅ Successfully uploaded to Pinecone!

**Meeting ID:** `{meeting_id}`
**Documents Created:** {len(docs)}
**Average Chunk Size:** {avg_chunk_size} characters
**Date:** {meeting_date}

You can now ask me questions about this meeting! For example:
- "What were the key decisions in {meeting_id}?"
- "Summarize the action items from this meeting"
- "What meetings do I have available?"
"""
        
    except Exception as e:
        return f"❌ Error uploading to Pinecone: {str(e)}"


@tool
def cancel_video_workflow() -> str:
    """
    Cancel the current video upload/transcription workflow and return to normal chat.
    
    Use this tool when the user wants to stop the video workflow and do something else.
    
    Returns:
        Confirmation message
        
    Example:
        User: "Never mind, I don't want to upload a video"
        Agent: calls cancel_video_workflow() -> resets state
    """
    reset_video_state()
    return "✅ Video workflow cancelled. What else can I help you with?"


# Export all tools and utilities
__all__ = [
    "initialize_video_tools",
    "get_video_state",
    "reset_video_state",
    "request_video_upload",
    "transcribe_uploaded_video",
    "request_transcription_edit",
    "update_transcription",
    "upload_transcription_to_pinecone",
    "cancel_video_workflow"
]
