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
from src.config.settings import Config


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
        
        # ---------------------------------------------------------
        # INTELLIGENT METADATA EXTRACTION (Immediate)
        # ---------------------------------------------------------
        try:
            from src.processing.metadata_extractor import MetadataExtractor
            extractor = MetadataExtractor()
            
            print("🧠 Extracting intelligent metadata (title, summary, date)...")
            extracted_data = extractor.extract_metadata(_video_state["transcription_text"])
            
            # Store metadata in state for later use
            _video_state["extracted_metadata"] = extracted_data
            
            # Apply speaker mapping if found
            if extracted_data.get("speaker_mapping"):
                print(f"👥 Applying speaker mapping: {extracted_data['speaker_mapping']}")
                _video_state["transcription_text"] = extractor.apply_speaker_mapping(
                    _video_state["transcription_text"], 
                    extracted_data["speaker_mapping"]
                )
                # Note: We are NOT updating segments here as it's complex, 
                # but the main text (used for RAG) is updated.
            
            # Prepend summary to transcript for better RAG indexing
            title = extracted_data.get("title", "Meeting")
            summary = extracted_data.get("summary", "")
            meeting_date = extracted_data.get("meeting_date")
            
            if summary:
                summary_header = f"# {title}\n\n"
                if meeting_date:
                    summary_header += f"**Date:** {meeting_date}\n\n"
                summary_header += f"**Summary:** {summary}\n\n---\n\n"
                
                _video_state["transcription_text"] = summary_header + _video_state["transcription_text"]
                print(f"📝 Added summary to transcript for indexing")
                
        except Exception as e:
            print(f"⚠️ Metadata extraction failed: {e}")
            _video_state["extracted_metadata"] = {}

        _video_state["transcription_in_progress"] = False
        _video_state["show_video_upload"] = False
        
        # Extract key statistics
        speakers_count = result.get("speakers_count", 0)
        processing_time = result.get("processing_time", 0)
        
        # Create a preview of the UPDATED transcript
        updated_text = _video_state["transcription_text"]
        transcript_preview = updated_text[:1000] + "..." if len(updated_text) > 1000 else updated_text
        
        # Get extracted info for display
        title = _video_state.get("extracted_metadata", {}).get("title", "Untitled Meeting")
        summary = _video_state.get("extracted_metadata", {}).get("summary", "No summary available.")
        
        # Return formatted transcription with summary (hide temp path)
        return f"""✅ **Transcription Complete!**

**File:** {filename}
**Title:** {title}
**Summary:** {summary}
**Processing Time:** {processing_time:.1f}s
**Speakers Identified:** {speakers_count}

---

**Transcript Preview (first 1000 characters with Speaker Names):**

{transcript_preview}

---

💡 **Note:** The full transcript is available in the **'Edit Transcript' tab**. Click "Load Transcript" to view and edit the complete text.

**What would you like to do next?**
1. 💾 Upload this transcription to Pinecone for AI-powered search
2. 📖 **View/Edit the full transcript** (go to the **"Edit Transcript" tab**, click "Load Transcript" to read the complete text, make any edits if needed, then "Save & Upload to Pinecone")
3. ❌ Cancel and start over

Just let me know!"""
        
    except Exception as e:
        _video_state["transcription_in_progress"] = False
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in transcribe_uploaded_video: {error_details}")
        return f"❌ Error during transcription: {str(e)}"


@tool               # <-- This tool is maybe not needed!! It is done in the UI (second tab)
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
        # Import MetadataExtractor
        from src.processing.metadata_extractor import MetadataExtractor
        
        # Check if we already extracted metadata in Step 1
        if "extracted_metadata" in _video_state and _video_state["extracted_metadata"]:
            print("🧠 Using pre-extracted metadata from transcription step.")
            extracted_data = _video_state["extracted_metadata"]
        else:
            # Fallback: Extract now if not done (e.g. legacy state)
            extractor = MetadataExtractor()
            print("🧠 Extracting intelligent metadata (title, summary, date)...")
            extracted_data = extractor.extract_metadata(_video_state["transcription_text"])
            
            # Apply speaker mapping if found
            if extracted_data.get("speaker_mapping"):
                print(f"👥 Applying speaker mapping: {extracted_data['speaker_mapping']}")
                _video_state["transcription_text"] = extractor.apply_speaker_mapping(
                    _video_state["transcription_text"], 
                    extracted_data["speaker_mapping"]
                )
        
        # Generate unique meeting ID
        meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        
        # Use extracted date if available, else today
        meeting_date = extracted_data.get("meeting_date") or datetime.now().strftime("%Y-%m-%d")
        
        # Create comprehensive metadata with consistent field names
        video_filename = os.path.basename(_video_state["uploaded_video_path"]) if _video_state["uploaded_video_path"] else "unknown"
        
        meeting_metadata = {
            "meeting_id": meeting_id,
            "meeting_date": meeting_date,  # ✅ Fixed: was "date"
            "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
            "source": "video_upload",
            "meeting_title": extracted_data.get("title", f"Meeting {meeting_date}"),  # ✅ Fixed: was "title"
            "summary": extracted_data.get("summary", "No summary available."),  # ✅ Added to metadata
            "speaker_mapping": extracted_data.get("speaker_mapping", {}),  # ✅ Added speaker mapping
            "source_file": video_filename,
            "transcription_model": Config.WHISPER_MODEL,
            "language": "en"
        }
        
        # Process transcription into documents
        segments = _video_state.get("transcription_segments", [])
        
        # Calculate duration and format as MM:SS
        total_duration_seconds = segments[-1]["end"] if segments else 0
        minutes = int(total_duration_seconds // 60)
        seconds = int(total_duration_seconds % 60)
        formatted_duration = f"{minutes:02d}:{seconds:02d}"
        
        # Add duration to metadata
        meeting_metadata["duration"] = formatted_duration
        
        docs = process_transcript_to_documents(
            _video_state["transcription_text"],
            segments,
            meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        # Upload to Pinecone
        _pinecone_manager.upsert_documents(docs)
        
        # Calculate statistics
        avg_chunk_size = sum(d.metadata['char_count'] for d in docs) // len(docs) if docs else 0
        
        # Reset state after successful upload
        reset_video_state()
        
        return f"""✅ Successfully uploaded to Pinecone!

**Meeting ID:** `{meeting_id}`
**Title:** {meeting_metadata['title']}
**Date:** {meeting_date}
**Summary:** {meeting_metadata['summary']}
**Documents Created:** {len(docs)}
**Duration:** {formatted_duration}

You can now ask me questions about this meeting!"""
        
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


@tool
def update_speaker_names(speaker_mapping: str) -> str:
    """
    Update speaker names in the current transcript by replacing generic labels (SPEAKER_00, SPEAKER_01, etc.) 
    with real names provided by the user.
    
    Args:
        speaker_mapping: A string describing the mapping in format "SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones"
                        or "0=John, 1=Sarah" (the tool will handle both formats)
    
    Returns:
        Confirmation message with the updated speaker list
        
    Example:
        User: "SPEAKER_00 is John Smith and SPEAKER_01 is Sarah Jones"
        Agent: calls update_speaker_names("SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones")
        
        User: "Speaker 0 is John and speaker 1 is Sarah"
        Agent: calls update_speaker_names("0=John, 1=Sarah")
    """
    if not _video_state.get("transcription_text"):
        return "❌ No transcription available. Please transcribe a video first."
    
    try:
        from src.processing.metadata_extractor import MetadataExtractor
        
        # Parse the speaker_mapping string into a dictionary
        mapping = {}
        
        # Split by comma and process each mapping
        pairs = [pair.strip() for pair in speaker_mapping.split(',')]
        
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Normalize the key to SPEAKER_XX format
                if key.isdigit():
                    key = f"SPEAKER_{int(key):02d}"
                elif not key.startswith("SPEAKER_"):
                    # Try to extract number from formats like "Speaker 0" or "speaker0"
                    import re
                    match = re.search(r'\d+', key)
                    if match:
                        key = f"SPEAKER_{int(match.group()):02d}"
                
                mapping[key] = value
        
        if not mapping:
            return "❌ Could not parse speaker mapping. Please use format: 'SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones' or '0=John, 1=Sarah'"
        
        # Apply the mapping
        extractor = MetadataExtractor()
        original_text = _video_state["transcription_text"]
        updated_text = extractor.apply_speaker_mapping(original_text, mapping)
        
        # Update the state
        _video_state["transcription_text"] = updated_text
        
        # Also update the extracted_metadata if it exists
        if "extracted_metadata" in _video_state:
            if "speaker_mapping" not in _video_state["extracted_metadata"]:
                _video_state["extracted_metadata"]["speaker_mapping"] = {}
            _video_state["extracted_metadata"]["speaker_mapping"].update(mapping)
        
        # Count replacements
        changes = []
        for old, new in mapping.items():
            if old in original_text:
                changes.append(f"{old} → {new}")
        
        if changes:
            return f"""✅ **Speaker names updated successfully!**

**Changes made:**
{chr(10).join(f"- {change}" for change in changes)}

The transcript has been updated. You can:
1. View it in the **"Edit Transcript"** tab by clicking "Load Transcript"
2. Upload it to Pinecone with the new names
"""
        else:
            return f"⚠️ No speakers found matching: {', '.join(mapping.keys())}. The transcript may already have these names updated, or the speaker labels are different."
            
    except Exception as e:
        return f"❌ Error updating speaker names: {str(e)}"


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
    "cancel_video_workflow",
    "update_speaker_names"
]
