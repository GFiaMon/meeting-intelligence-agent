# Intelligent Metadata Extraction - Implementation Summary

## Overview
The Meeting Intelligence Agent now automatically extracts rich metadata from transcriptions using AI, providing immediate insights and improving search capabilities.

## Features Implemented

### 1. **Automatic Title Generation**
- **What it does**: Generates a meaningful, concise title for each meeting based on content
- **Example**: Instead of "Meeting 2024-12-04", you get "Q4 Marketing Strategy Review"
- **When**: Immediately after transcription completes
- **Model**: Uses `gpt-4o-mini` (cost-effective)

### 2. **Meeting Summary**
- **What it does**: Creates a 2-3 sentence summary of the meeting
- **Example**: "The team discussed the Q4 marketing budget and timeline. Sarah presented the new campaign strategy. Action items were assigned to John and Mike."
- **When**: Immediately after transcription
- **Benefit**: Quick overview without reading the full transcript

### 3. **Speaker Name Identification**
- **What it does**: Attempts to map generic speaker labels (SPEAKER_00, SPEAKER_01) to real names
- **How**: Analyzes introductions and context in the conversation
- **Example**: "SPEAKER_00" → "John Smith", "SPEAKER_01" → "Sarah Jones"
- **Result**: The transcript text is automatically updated with real names
- **When**: Immediately after transcription

### 4. **Meeting Date Extraction**
- **What it does**: Extracts the actual meeting date from the conversation if mentioned
- **Example**: If someone says "Welcome to our October 12th meeting", it extracts "2024-10-12"
- **Fallback**: Uses transcription date if not mentioned
- **Metadata**: Stores both `meeting_date` (actual) and `date_transcribed`

### 5. **Duration Formatting**
- **What it does**: Formats meeting duration as "MM:SS" instead of raw seconds
- **Example**: "45:30" instead of "2730.5"
- **Benefit**: Human-readable format in metadata and UI

## Where You See It

### In the Chat (After Transcription)
```
✅ Transcription Complete!

**File:** team_meeting.mp4
**Title:** Q4 Marketing Strategy Review
**Summary:** The team discussed the Q4 marketing budget...
**Processing Time:** 45.2s
**Speakers Identified:** 3

---

**Transcript Preview (with Speaker Names):**
John Smith: Welcome everyone to our Q4 strategy meeting...
Sarah Jones: Thanks John. I'd like to start with the budget...
```

### In Pinecone Metadata
All extracted information is stored as searchable metadata:
- `title`: "Q4 Marketing Strategy Review"
- `summary`: "The team discussed..."
- `meeting_date`: "2024-10-12"
- `date_transcribed`: "2024-12-04"
- `duration`: "45:30"
- `meeting_id`: "meeting_abc12345"
- `source_file`: "team_meeting.mp4"

### In the "Manage Meetings" Tab
The table now shows:
- Meeting ID
- **Title** (auto-generated)
- Date
- **Duration** (formatted)
- Source File

## Cost Optimization

### Single LLM Call Per Transcription
- Metadata extraction happens **once** after transcription
- Results are cached in `_video_state`
- When you upload to Pinecone, it reuses the cached metadata (no second LLM call)

### Cheap Model for Extraction
- Uses `gpt-4o-mini` instead of the main agent model
- Configured in `src/config/settings.py` as `METADATA_MODEL`
- ~30x cheaper than GPT-4o for this task

### Token Savings in Chat
- Only a **preview** (first 1000 chars) is sent to the chat agent
- Full transcript is NOT added to conversation history
- Saves thousands of tokens per conversation

## Technical Implementation

### Files Modified
1. **`src/processing/metadata_extractor.py`** (NEW)
   - `MetadataExtractor` class
   - Uses structured JSON output from LLM
   - Handles speaker name replacement

2. **`src/tools/video.py`**
   - `transcribe_uploaded_video`: Runs extraction immediately
   - `upload_transcription_to_pinecone`: Reuses cached metadata

3. **`src/ui/gradio_app.py`**
   - `save_and_upload_transcript`: Uses extraction for manual uploads

4. **`src/config/settings.py`**
   - Added `METADATA_MODEL = "gpt-4o-mini"`

### Workflow
```
1. User uploads video
2. WhisperX transcribes → raw text with SPEAKER_00, SPEAKER_01
3. MetadataExtractor analyzes:
   - Generates title
   - Creates summary
   - Extracts date
   - Identifies speaker names
4. Speaker names replace generic labels in transcript
5. All metadata stored in _video_state
6. User sees enriched preview in chat
7. User uploads to Pinecone → reuses cached metadata
8. Pinecone stores documents with rich, searchable metadata
```

## Benefits

### For Users
- **Immediate Insights**: See title and summary without reading full transcript
- **Better Organization**: Meaningful titles instead of dates
- **Readable Transcripts**: Real names instead of "SPEAKER_00"
- **Faster Search**: Rich metadata enables precise filtering

### For Developers
- **Cost Efficient**: Single cheap LLM call per transcription
- **Scalable**: Cached results prevent redundant processing
- **Flexible**: Easy to add more extraction fields in the future

## Future Enhancements (Possible)
- Extract action items automatically
- Identify key decisions and store as metadata
- Detect meeting type (standup, review, planning)
- Extract attendee list from context
- Sentiment analysis per speaker

## Testing
To test the features:
1. Upload a video with clear introductions
2. Check the transcription output for title and summary
3. Go to "Edit Transcript" tab to see full text with speaker names
4. Upload to Pinecone
5. Check "Manage Meetings" tab to see the title and duration
6. Query the meeting to verify metadata is searchable
