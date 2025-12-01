import os
from datetime import datetime

def format_to_display_and_rag(diarized_segments: list):
    """
    Formats the diarized segments for display and RAG.
    Returns a tuple: (display_text: str, rag_ready_segments: list).
    """
    display_text = "## 🎯 Video Transcription with Speaker Identification\n\n"
    rag_ready_segments = []
    
    current_speaker = None
    
    for segment in diarized_segments:
        speaker = segment.get("speaker", "UNKNOWN")
        start_time = format_timestamp(segment["start"])
        text = segment["text"].strip()
        
        # Format for display
        if speaker != current_speaker:
            display_text += f"\n**👤 {speaker}:**\n"
            current_speaker = speaker
        display_text += f"[{start_time}] {text}\n"
        
        # Format for RAG
        rag_ready_segments.append({
            'content': text,
            'metadata': {
                'start': segment['start'],
                'end': segment['end'],
                'speaker': speaker
            }
        })
        
    # Add summary
    speakers = set(segment.get("speaker", "UNKNOWN") for segment in diarized_segments)
    display_text += f"\n---\n**Speakers Detected:** {len(speakers)} | **Segments:** {len(diarized_segments)}"
        
    return display_text, rag_ready_segments

def format_timestamp(seconds):
    """Convert seconds to MM:SS format"""
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def generate_timing_info(segments, processing_time, video_file, device):
    """Generate timing statistics."""
    if not segments:
        return "No timing information available"
    
    total_duration = segments[-1]["end"]
    speed_ratio = total_duration / processing_time if processing_time > 0 else 0
    video_name = os.path.basename(video_file) if video_file else "Unknown"
    
    return f"""
## ⏱️ Processing Statistics

**Video File:** {video_name}
**Audio Duration:** {format_timestamp(total_duration)}
**Processing Time:** {processing_time:.1f} seconds
**Speed Ratio:** {speed_ratio:.2f}x
**Status:** {"Faster than real-time" if speed_ratio > 1 else "Slower than real-time"}
**Device:** {device.upper()}
**Completed:** {datetime.now().strftime("%H:%M:%S")}
"""
