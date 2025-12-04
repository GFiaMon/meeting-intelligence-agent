import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from datetime import datetime

def process_transcript_to_documents(
    transcript_text, 
    speaker_data, 
    meeting_id,
    meeting_metadata=None,
    min_chunk_size=1500,    # Increased from 500 for better RAG context
    max_chunk_size=3000,    # Increased from 1500 for richer chunks
    chunk_overlap=200       # Increased from 100 for better continuity
):
    """
    Process transcript text and speaker data into LangChain Documents with semantic grouping.
    
    Groups consecutive speaker segments into meaningful chunks with rich metadata for better RAG.
    
    Args:
        transcript_text (str): The full transcript text.
        speaker_data (list): List of dictionaries containing segment info (text, start, end, speaker).
        meeting_id (str): Unique identifier for the meeting.
        meeting_metadata (dict, optional): Additional metadata (meeting_date, source_file, etc.).
        min_chunk_size (int): Minimum characters per chunk (default: 1500).
        max_chunk_size (int): Maximum characters per chunk (default: 3000).
        chunk_overlap (int): Character overlap between chunks (default: 200).
        
    Returns:
        list[Document]: List of processed LangChain Documents with rich metadata.
    """
    if not speaker_data:
        # Fallback: use RecursiveCharacterTextSplitter on raw text
        return _fallback_chunking(transcript_text, meeting_id, meeting_metadata, min_chunk_size, max_chunk_size, chunk_overlap)
    
    # Initialize metadata defaults
    meeting_metadata = meeting_metadata or {}
    
    # Group segments into meaningful chunks
    chunks = []
    current_chunk = {
        "text": "",
        "speaker": None,
        "speakers": set(),
        "start_time": None,
        "end_time": None,
        "segment_count": 0
    }
    
    def finalize_chunk():
        """Finalize the current chunk and add to chunks list."""
        if current_chunk["text"].strip():
            chunks.append({
                "text": current_chunk["text"].strip(),
                "speaker": current_chunk["speaker"],
                "speakers": list(current_chunk["speakers"]),
                "start_time": current_chunk["start_time"],
                "end_time": current_chunk["end_time"],
                "segment_count": current_chunk["segment_count"]
            })
        # Reset current chunk
        current_chunk["text"] = ""
        current_chunk["speaker"] = None
        current_chunk["speakers"] = set()
        current_chunk["start_time"] = None
        current_chunk["end_time"] = None
        current_chunk["segment_count"] = 0
    
    # Process segments with semantic grouping
    for segment in speaker_data:
        text = segment.get("text", "").strip()
        if not text:
            continue
        
        speaker = segment.get("speaker", "UNKNOWN")
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        
        # Initialize chunk if empty
        if current_chunk["speaker"] is None:
            current_chunk["speaker"] = speaker
            current_chunk["start_time"] = start
        
        # Check if we should finalize the current chunk
        current_length = len(current_chunk["text"])
        new_length = current_length + len(text) + 1  # +1 for space
        
        should_finalize = False
        
        # Finalize if we exceed max_chunk_size
        if new_length > max_chunk_size and current_length >= min_chunk_size:
            should_finalize = True
        
        # Finalize if speaker changes AND we've met min_chunk_size
        elif speaker != current_chunk["speaker"] and current_length >= min_chunk_size:
            should_finalize = True
        
        if should_finalize:
            finalize_chunk()
            # Start new chunk with current segment
            current_chunk["speaker"] = speaker
            current_chunk["start_time"] = start
        
        # Add segment to current chunk
        if current_chunk["text"]:
            current_chunk["text"] += " " + text
        else:
            current_chunk["text"] = text
        
        current_chunk["speakers"].add(speaker)
        current_chunk["end_time"] = end
        current_chunk["segment_count"] += 1
    
    # Finalize the last chunk
    finalize_chunk()
    
    # Apply overlap between chunks
    chunks_with_overlap = _apply_overlap(chunks, chunk_overlap)
    
    # Convert chunks to LangChain Documents with rich metadata
    documents = []
    total_chunks = len(chunks_with_overlap)
    
    for idx, chunk in enumerate(chunks_with_overlap):
        # Build comprehensive metadata with all available fields
        # Note: Pinecone only accepts string/number/boolean/list metadata, so we convert dicts to JSON strings
        speaker_mapping = meeting_metadata.get("speaker_mapping", {})
        speaker_mapping_json = json.dumps(speaker_mapping) if speaker_mapping else "{}"  # Convert dict to JSON string
        
        metadata = {
            # Meeting Identification
            "meeting_id": meeting_id,
            "meeting_date": meeting_metadata.get("meeting_date", datetime.now().strftime("%Y-%m-%d")),
            "meeting_title": meeting_metadata.get("meeting_title", ""),
            "summary": meeting_metadata.get("summary", ""),  # ✅ Added summary
            
            # Temporal Information
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"],
            "duration": chunk["end_time"] - chunk["start_time"],
            "start_time_formatted": _format_timestamp(chunk["start_time"]),
            "end_time_formatted": _format_timestamp(chunk["end_time"]),
            "meeting_duration": meeting_metadata.get("duration", "N/A"),  # ✅ Added total meeting duration
            
            # Speaker Information
            "speaker": chunk["speaker"],
            "speakers": chunk["speakers"],
            "speaker_count": len(chunk["speakers"]),
            "speaker_mapping": speaker_mapping_json,  # ✅ Converted to JSON string for Pinecone compatibility
            
            # Content Metadata
            "chunk_type": "conversation_turn" if len(chunk["speakers"]) == 1 else "mixed_speakers",
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "word_count": len(chunk["text"].split()),
            "char_count": len(chunk["text"]),
            "segment_count": chunk["segment_count"],
            
            # Source Information
            "source": meeting_metadata.get("source", "unknown"),  # ✅ Added source type
            "source_file": meeting_metadata.get("source_file", ""),
            "transcription_model": meeting_metadata.get("transcription_model", "whisperx"),
            "language": meeting_metadata.get("language", "en"),
            "date_transcribed": meeting_metadata.get("date_transcribed", datetime.now().strftime("%Y-%m-%d")),  # ✅ Added transcription date
        }
        
        doc = Document(page_content=chunk["text"], metadata=metadata)
        documents.append(doc)
    
    return documents


def _apply_overlap(chunks, overlap_size):
    """
    Apply overlap between consecutive chunks by including trailing text from previous chunk.
    
    Args:
        chunks (list): List of chunk dictionaries.
        overlap_size (int): Number of characters to overlap.
        
    Returns:
        list: Chunks with overlap applied.
    """
    if overlap_size <= 0 or len(chunks) <= 1:
        return chunks
    
    overlapped_chunks = [chunks[0]]  # First chunk has no overlap
    
    for i in range(1, len(chunks)):
        current = chunks[i].copy()
        previous = chunks[i - 1]
        
        # Get overlap text from previous chunk
        overlap_text = previous["text"][-overlap_size:].strip()
        
        # Prepend overlap to current chunk
        if overlap_text:
            current["text"] = overlap_text + " " + current["text"]
            # Update start_time to include overlap context (keep previous chunk's end region)
            # Note: We keep the original start_time for temporal accuracy
        
        overlapped_chunks.append(current)
    
    return overlapped_chunks


def _fallback_chunking(transcript_text, meeting_id, meeting_metadata, min_chunk_size, max_chunk_size, chunk_overlap):
    """
    Fallback chunking when no speaker data is available.
    Uses RecursiveCharacterTextSplitter on the raw transcript.
    
    Args:
        transcript_text (str): Full transcript text.
        meeting_id (str): Meeting identifier.
        meeting_metadata (dict): Meeting metadata.
        min_chunk_size (int): Minimum chunk size.
        max_chunk_size (int): Maximum chunk size.
        chunk_overlap (int): Overlap size.
        
    Returns:
        list[Document]: Chunked documents.
    """
    meeting_metadata = meeting_metadata or {}
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # Create comprehensive base metadata with consistent field names
    # Note: Pinecone only accepts string/number/boolean/list metadata, so we convert dicts to JSON strings
    speaker_mapping = meeting_metadata.get("speaker_mapping", {})
    speaker_mapping_json = json.dumps(speaker_mapping) if speaker_mapping else "{}"  # Convert dict to JSON string
    
    base_metadata = {
        "meeting_id": meeting_id,
        "meeting_date": meeting_metadata.get("meeting_date", datetime.now().strftime("%Y-%m-%d")),
        "meeting_title": meeting_metadata.get("meeting_title", ""),
        "summary": meeting_metadata.get("summary", ""),  # ✅ Added summary
        "chunk_type": "full_transcript_chunk",
        "source": meeting_metadata.get("source", "unknown"),  # ✅ Added source
        "source_file": meeting_metadata.get("source_file", ""),
        "transcription_model": meeting_metadata.get("transcription_model", "whisperx"),
        "language": meeting_metadata.get("language", "en"),
        "date_transcribed": meeting_metadata.get("date_transcribed", datetime.now().strftime("%Y-%m-%d")),  # ✅ Added transcription date
        "speaker_mapping": speaker_mapping_json,  # ✅ Converted to JSON string for Pinecone compatibility
        "meeting_duration": meeting_metadata.get("duration", "N/A"),  # ✅ Added duration
    }
    
    # Split text into chunks
    texts = text_splitter.split_text(transcript_text)
    
    # Create documents with metadata
    documents = []
    total_chunks = len(texts)
    
    for idx, text in enumerate(texts):
        metadata = base_metadata.copy()
        metadata.update({
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "word_count": len(text.split()),
            "char_count": len(text),
        })
        
        doc = Document(page_content=text, metadata=metadata)
        documents.append(doc)
    
    return documents


def _format_timestamp(seconds):
    """
    Convert seconds to MM:SS format.
    
    Args:
        seconds (float): Time in seconds.
        
    Returns:
        str: Formatted timestamp (MM:SS).
    """
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
