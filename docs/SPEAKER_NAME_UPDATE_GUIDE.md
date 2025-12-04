# Manual Speaker Name Updates

## Overview
You can now manually update speaker names in your transcripts through conversational interaction with the agent. This is useful when:
- The automatic speaker identification didn't work
- You want to correct speaker names
- You know the speakers but they didn't introduce themselves

## How to Use

### After Transcription
Once you've transcribed a video, you can tell the agent to update speaker names in several natural ways:

### Example Conversations

#### Option 1: Direct Format
```
You: "Update the speaker names: SPEAKER_00 is John Smith and SPEAKER_01 is Sarah Jones"

Agent: [calls update_speaker_names("SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones")]
✅ Speaker names updated successfully!

Changes made:
- SPEAKER_00 → John Smith
- SPEAKER_01 → Sarah Jones

The transcript has been updated. You can:
1. View it in the "Edit Transcript" tab by clicking "Load Transcript"
2. Upload it to Pinecone with the new names
```

#### Option 2: Casual Format
```
You: "Speaker 0 is John and speaker 1 is Sarah"

Agent: [calls update_speaker_names("0=John, 1=Sarah")]
✅ Speaker names updated successfully!
```

#### Option 3: Natural Language
```
You: "The first speaker is John Smith and the second one is Sarah Jones"

Agent: [understands and calls update_speaker_names("0=John Smith, 1=Sarah Jones")]
✅ Speaker names updated successfully!
```

## Supported Formats

The tool accepts multiple formats:

1. **Full format**: `SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones`
2. **Short format**: `0=John, 1=Sarah`
3. **Mixed**: `SPEAKER_00=John, 1=Sarah`

The tool automatically normalizes all formats to the correct `SPEAKER_XX` format.

## What Happens

1. **Parsing**: The agent parses your speaker mapping
2. **Validation**: Checks if the transcript exists
3. **Replacement**: Replaces all occurrences of the old labels with new names
4. **Update**: Updates `_video_state["transcription_text"]`
5. **Metadata**: Updates `extracted_metadata["speaker_mapping"]` for future reference
6. **Confirmation**: Shows you what changed

## Viewing the Updated Transcript

After updating speaker names, you can:

### Option 1: Edit Transcript Tab
1. Go to the **"Edit Transcript"** tab
2. Click **"Load Transcript"**
3. You'll see the full transcript with updated names

### Option 2: Upload to Pinecone
```
You: "Upload this to Pinecone"

Agent: [calls upload_transcription_to_pinecone()]
✅ Successfully uploaded to Pinecone!

The transcript with updated speaker names is now searchable.
```

## Complete Workflow Example

```
1. You: [Upload video]

2. Agent: [Transcribes video]
   ✅ Transcription Complete!
   **Speakers Identified:** 2
   [Shows preview with SPEAKER_00, SPEAKER_01]

3. You: "Update speaker names: 0 is John Smith, 1 is Sarah Jones"

4. Agent: ✅ Speaker names updated successfully!
   Changes made:
   - SPEAKER_00 → John Smith
   - SPEAKER_01 → Sarah Jones

5. You: "Upload to Pinecone"

6. Agent: ✅ Successfully uploaded to Pinecone!
   **Title:** Q4 Strategy Meeting
   **Summary:** John and Sarah discussed...
   
   [Transcript now has real names throughout]
```

## Technical Details

### Tool Signature
```python
@tool
def update_speaker_names(speaker_mapping: str) -> str:
    """
    Update speaker names in the current transcript.
    
    Args:
        speaker_mapping: String like "SPEAKER_00=John, SPEAKER_01=Sarah"
                        or "0=John, 1=Sarah"
    
    Returns:
        Confirmation message with changes made
    """
```

### What Gets Updated
1. `_video_state["transcription_text"]` - The main transcript text
2. `_video_state["extracted_metadata"]["speaker_mapping"]` - Metadata record

### Persistence
- The updated names persist in `_video_state` until you upload to Pinecone or reset
- Once uploaded to Pinecone, the names are permanently stored in the indexed documents
- The Edit Transcript tab always shows the current state

## Tips

1. **Update before uploading**: Change names before uploading to Pinecone for best results
2. **Check the Edit tab**: Always verify the changes look correct
3. **Multiple updates**: You can update names multiple times if needed
4. **Partial updates**: You can update just one speaker at a time

## Error Handling

### No Transcript Available
```
You: "Update speaker 0 to John"
Agent: ❌ No transcription available. Please transcribe a video first.
```

### Invalid Format
```
You: "Update speakers: John and Sarah"
Agent: ❌ Could not parse speaker mapping. Please use format: 
'SPEAKER_00=John Smith, SPEAKER_01=Sarah Jones' or '0=John, 1=Sarah'
```

### Speaker Not Found
```
You: "Update SPEAKER_05 to Mike"
Agent: ⚠️ No speakers found matching: SPEAKER_05. 
The transcript may already have these names updated, or the speaker labels are different.
```

## Integration with Auto-Detection

This manual tool complements the automatic speaker identification:

1. **Auto-detection runs first** during transcription
2. **If it works**: Names are already updated
3. **If it doesn't**: You can manually update using this tool
4. **Best of both worlds**: Automatic when possible, manual when needed

## Future Enhancements

Potential improvements:
- Ask the agent to list current speakers first
- Bulk update from a file
- Remember speaker names across sessions
- Suggest names based on previous meetings
