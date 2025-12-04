# Pinecone Metadata Schema

## Overview
This document defines the **standardized metadata schema** used across all Pinecone document uploads in the Meeting Intelligence Agent system. All scripts that create or query Pinecone documents MUST use these exact field names.

## Core Metadata Fields

### Meeting Identification
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| `meeting_id` | string | ✅ Yes | Unique identifier for the meeting | `"meeting_abc12345"` |
| `meeting_date` | string | ✅ Yes | Date of the meeting (YYYY-MM-DD) | `"2024-12-04"` |
| `meeting_title` | string | ✅ Yes | Title/subject of the meeting | `"Q4 Strategy Review"` |
| `summary` | string | ✅ Yes | Brief summary of the meeting | `"Discussed Q4 goals..."` |

### Temporal Information
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| `start_time` | float | ⚠️ Optional* | Chunk start time in seconds | `125.5` |
| `end_time` | float | ⚠️ Optional* | Chunk end time in seconds | `185.2` |
| `duration` | float | ⚠️ Optional* | Chunk duration (end - start) | `59.7` |
| `start_time_formatted` | string | ⚠️ Optional* | Human-readable start time | `"02:05"` |
| `end_time_formatted` | string | ⚠️ Optional* | Human-readable end time | `"03:05"` |
| `meeting_duration` | string | ✅ Yes | Total meeting duration | `"45:30"` |
| `date_transcribed` | string | ✅ Yes | Date when transcribed (YYYY-MM-DD) | `"2024-12-04"` |

*Only available for video transcriptions with speaker data

### Speaker Information
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| `speaker` | string | ⚠️ Optional* | Primary speaker in chunk | `"John Smith"` |
| `speakers` | list | ⚠️ Optional* | All speakers in chunk | `["John Smith", "Sarah Jones"]` |
| `speaker_count` | int | ⚠️ Optional* | Number of speakers in chunk | `2` |
| `speaker_mapping` | **string (JSON)** | ✅ Yes | **JSON string** mapping SPEAKER_XX to real names | `"{\"SPEAKER_00\": \"John Smith\"}"` |

**⚠️ IMPORTANT**: `speaker_mapping` must be stored as a **JSON string**, not a dict. Pinecone only accepts string/number/boolean/list metadata values.

*Only available for video transcriptions with speaker data

### Content Metadata
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| `chunk_type` | string | ✅ Yes | Type of chunk | `"conversation_turn"` or `"mixed_speakers"` or `"full_transcript_chunk"` |
| `chunk_index` | int | ✅ Yes | Index of this chunk (0-based) | `5` |
| `total_chunks` | int | ✅ Yes | Total number of chunks | `42` |
| `word_count` | int | ✅ Yes | Number of words in chunk | `250` |
| `char_count` | int | ✅ Yes | Number of characters in chunk | `1523` |
| `segment_count` | int | ⚠️ Optional* | Number of segments in chunk | `8` |

*Only available for video transcriptions with speaker data

### Source Information
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| `source` | string | ✅ Yes | Source type | `"video_upload"`, `"video_upload_edited"`, `"Manual Entry"`, `"Notion"` |
| `source_file` | string | ✅ Yes | Original filename or identifier | `"meeting_recording.mp4"` |
| `transcription_model` | string | ✅ Yes | Model used for transcription | `"whisperx-small"`, `"text_import"` |
| `language` | string | ✅ Yes | Language code | `"en"` |

---

## Usage Examples

### Example 1: Video Transcription Upload
```python
meeting_metadata = {
    "meeting_id": "meeting_abc12345",
    "meeting_date": "2024-12-04",
    "meeting_title": "Q4 Strategy Review",
    "summary": "Discussed Q4 goals, budget allocation, and team structure.",
    "speaker_mapping": "{\"SPEAKER_00\": \"John Smith\", \"SPEAKER_01\": \"Sarah Jones\"}",  # JSON string, not dict!
    "meeting_duration": "45:30",
    "date_transcribed": "2024-12-04",
    "source": "video_upload",
    "source_file": "meeting_recording.mp4",
    "transcription_model": "whisperx-small",
    "language": "en"
}
```

### Example 2: Text Import (Notion, Manual Notes)
```python
meeting_metadata = {
    "meeting_id": "doc_xyz78901",
    "meeting_date": "2024-12-03",
    "meeting_title": "Product Roadmap Discussion",
    "summary": "Imported from Notion",
    "speaker_mapping": "{}",  # Empty JSON string
    "meeting_duration": "N/A",
    "date_transcribed": "2024-12-04",
    "source": "Notion",
    "source_file": "notion_upload",
    "transcription_model": "text_import",
    "language": "en"
}
```

---

## Files Using This Schema

### Upstream (Creating Documents)
1. **`src/tools/video.py`** - Video transcription uploads
   - Function: `upload_transcription_to_pinecone()`
   
2. **`src/ui/gradio_app.py`** - Edited transcript uploads
   - Function: `save_and_upload_transcript()`
   
3. **`src/tools/general.py`** - Text/Notion imports
   - Function: `upsert_text_to_pinecone()`
   
4. **`src/zoom_mcp/processor.py`** - Zoom RTMS live transcriptions
   - Function: `process_message()`

### Processing Layer
5. **`src/retrievers/pipeline.py`** - Document chunking and metadata assignment
   - Function: `process_transcript_to_documents()`
   - Function: `_fallback_chunking()`

### Downstream (Querying Documents)
6. **`src/tools/general.py`** - Search and retrieval tools
   - Function: `search_meetings()`
   - Function: `get_meeting_metadata()`
   - Function: `list_recent_meetings()`

7. **`src/retrievers/pinecone.py`** - Pinecone manager
   - Function: `list_meetings()`

---

## Migration Notes

### Breaking Changes (2024-12-04)
- ❌ **REMOVED**: `date` → ✅ **USE**: `meeting_date`
- ❌ **REMOVED**: `title` → ✅ **USE**: `meeting_title`
- ✅ **ADDED**: `summary` (now required in all metadata)
- ✅ **ADDED**: `speaker_mapping` (now stored in metadata, not just applied to text)
- ✅ **ADDED**: `source` (to distinguish upload types)
- ✅ **ADDED**: `date_transcribed` (when the transcription was created)
- ✅ **ADDED**: `meeting_duration` (total meeting length)

### Backward Compatibility
Existing documents in Pinecone may still use old field names (`date`, `title`). Search functions should handle both:
```python
# Prefer new field names, fallback to old
meeting_date = metadata.get("meeting_date") or metadata.get("date", "N/A")
meeting_title = metadata.get("meeting_title") or metadata.get("title", "N/A")
```

---

## Validation Checklist

When creating new upload functions or modifying existing ones:

- [ ] All required fields are present
- [ ] Field names match this schema exactly (case-sensitive)
- [ ] `meeting_date` uses YYYY-MM-DD format
- [ ] `meeting_id` is unique and follows naming convention
- [ ] `summary` is meaningful (not empty or generic)
- [ ] `speaker_mapping` is a dict (empty dict if no speakers)
- [ ] `source` accurately describes the upload type
- [ ] `transcription_model` reflects the actual model used

---

## Contact
For questions or proposed changes to this schema, please update this document and notify the team.

**Last Updated**: 2024-12-04
**Version**: 2.0
