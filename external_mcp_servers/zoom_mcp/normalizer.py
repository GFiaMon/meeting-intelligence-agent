import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from langchain_core.documents import Document

class TranscriptNormalizer:
    """
    Normalizes transcript data from various sources (Zoom RTMS, manual notes)
    into the standard format used by the agent.
    """
    
    @staticmethod
    def normalize_zoom_chunk(chunk: Dict[str, Any], meeting_id: str) -> Optional[Document]:
        """
        Converts a Zoom RTMS transcript chunk into a LangChain Document.
        
        Expected Zoom JSON format (simplified):
        {
            "speaker_id": "user_123",
            "speaker_name": "John Doe",
            "text": "Hello world",
            "timestamp": 1634567890000, # ms
            "seq": 1
        }
        """
        try:
            text = chunk.get("text", "").strip()
            if not text:
                return None
                
            speaker = chunk.get("speaker_name", "Unknown Speaker")
            timestamp_ms = chunk.get("timestamp", 0)
            
            # Format timestamp to MM:SS relative to meeting start if possible, 
            # but for live streams we might just use the absolute time or 
            # a placeholder if we don't have start time. 
            # For now, let's use a simple timestamp format.
            # In a real app, we'd track meeting start time.
            
            # Create the formatted content string
            # Format: [TIMESTAMP] Speaker: Text
            # We'll use the actual time for the timestamp in the text for now
            dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
            time_str = dt.strftime("%H:%M:%S")
            
            formatted_content = f"[{time_str}] {speaker}: {text}"
            
            # Create comprehensive metadata following the standard schema
            metadata = {
                # Meeting Identification
                "meeting_id": meeting_id,
                "meeting_date": datetime.now().strftime("%Y-%m-%d"),
                "meeting_title": f"Zoom Live Meeting {meeting_id}",
                "summary": "Live Zoom transcription",
                
                # Temporal Information
                "timestamp": timestamp_ms,
                "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
                "meeting_duration": "N/A",  # Not available for live streams
                
                # Speaker Information
                "speaker": speaker,
                "speaker_mapping": "{}",  # Empty JSON string (Pinecone requires string, not dict)
                
                # Content Metadata
                "chunk_type": "zoom_rtms_chunk",
                "word_count": len(text.split()),
                "char_count": len(text),
                
                # Source Information
                "source": "zoom_rtms",
                "source_file": f"zoom_live_{meeting_id}",
                "transcription_model": "zoom_rtms",
                "language": "en",
                
                # Legacy fields for backward compatibility
                "type": "transcript_chunk"
            }
            
            return Document(page_content=formatted_content, metadata=metadata)
            
        except Exception as e:
            print(f"Error normalizing chunk: {e}")
            return None

    @staticmethod
    def normalize_manual_note(text: str, speaker: str, meeting_id: str) -> Document:
        """
        Converts a manual note into a LangChain Document.
        """
        timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M:%S")
        
        formatted_content = f"[{time_str}] {speaker}: {text}"
        
        # Create comprehensive metadata following the standard schema
        metadata = {
            # Meeting Identification
            "meeting_id": meeting_id,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_title": f"Manual Notes {meeting_id}",
            "summary": "Manual meeting notes",
            
            # Temporal Information
            "timestamp": timestamp.timestamp() * 1000,
            "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
            "meeting_duration": "N/A",
            
            # Speaker Information
            "speaker": speaker,
            "speaker_mapping": "{}",  # Empty JSON string (Pinecone requires string, not dict)
            
            # Content Metadata
            "chunk_type": "manual_note",
            "word_count": len(text.split()),
            "char_count": len(text),
            
            # Source Information
            "source": "manual_note",
            "source_file": f"manual_note_{meeting_id}",
            "transcription_model": "manual_entry",
            "language": "en",
            
            # Legacy fields for backward compatibility
            "type": "manual_note"
        }
        
        return Document(page_content=formatted_content, metadata=metadata)
