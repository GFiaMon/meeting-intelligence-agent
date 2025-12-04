# Managing Pinecone Meetings - Complete Guide

## Overview

This guide answers your two main questions:
1. **How to delete test transcriptions from Pinecone**
2. **Whether your app can filter by metadata and show different meetings**

---

## Question 1: How to Delete Test Transcriptions

### ✅ **Answer: YES - Multiple Methods Available**

I've added three ways to delete test transcriptions from Pinecone:

### **Method A: Using the Gradio UI (Recommended for Most Users)**

1. **Start your application:**
   ```bash
   python app_v4.py
   ```

2. **Navigate to the "📊 Manage Meetings" tab** (new tab added)

3. **Click "🔄 Refresh Meeting List"** to see all stored meetings

4. **Copy the Meeting ID** you want to delete (e.g., `meeting_abc12345`)

5. **Paste it in the "Meeting ID" field** and click "🗑️ Delete Meeting"

**Benefits:**
- ✅ User-friendly interface
- ✅ See all meetings before deleting
- ✅ Visual confirmation
- ✅ No coding required

---

### **Method B: Using the Command-Line Utility**

I've created a dedicated script for managing Pinecone data:

```bash
# List all meetings
python scripts/manage_pinecone.py list

# Delete a specific meeting
python scripts/manage_pinecone.py delete meeting_abc12345

# View statistics
python scripts/manage_pinecone.py stats

# Clear ALL data (use with caution!)
python scripts/manage_pinecone.py clear
```

**Benefits:**
- ✅ Fast and scriptable
- ✅ Great for automation
- ✅ Includes safety confirmations
- ✅ Shows detailed statistics

---

### **Method C: Using Python Code Directly**

For programmatic deletion or integration into other scripts:

```python
from src.retrievers.pinecone import PineconeManager

# Initialize Pinecone
pm = PineconeManager()

# List all meetings
meetings = pm.list_meetings(namespace="default")
for meeting in meetings:
    print(f"Meeting ID: {meeting['meeting_id']}")
    print(f"Title: {meeting['title']}")
    print(f"Date: {meeting['meeting_date']}")
    print()

# Delete a specific meeting
deleted_count = pm.delete_by_meeting_id("meeting_abc12345", namespace="default")
print(f"Deleted {deleted_count} vectors")

# Delete entire namespace (CAUTION!)
# pm.delete_namespace("default")
```

**Benefits:**
- ✅ Full programmatic control
- ✅ Can be integrated into workflows
- ✅ Useful for batch operations

---

## Question 2: Can Your App Filter by Metadata?

### ✅ **Answer: YES - Metadata Filtering is Already Implemented!**

Your app **already supports** metadata filtering and can show you different meetings. Here's how:

### **How It Works**

1. **Metadata Storage** - Each transcription chunk is stored with rich metadata:
   ```python
   {
       "meeting_id": "meeting_abc12345",
       "meeting_date": "2025-12-03",
       "title": "Project Planning Meeting",
       "speaker": "John Doe",
       "start_time": 120.5,
       "end_time": 135.2,
       "participants": ["John", "Jane", "Bob"],
       "source": "video_upload"
   }
   ```

2. **Automatic Filtering** - When you ask about a specific meeting, the RAG system automatically filters:
   ```python
   # In src/agents/rag_service.py (lines 34-46)
   meeting_id_match = re.search(r'meeting_([a-f0-9]{8})', query)
   
   if meeting_id and is_comprehensive:
       return {
           "k": 100,
           "filter": {"meeting_id": {"$eq": meeting_id}}
       }
   ```

3. **Pinecone Pre-filtering** - Pinecone filters BEFORE similarity search:
   - First: Get all vectors where `meeting_id == "meeting_abc12345"`
   - Then: Find top K most similar vectors from that filtered set
   - Result: Only results from that specific meeting

---

### **How to Use Metadata Filtering in Chat**

#### **Example 1: Query a Specific Meeting**
```
User: "Summarize meeting_abc12345"
```
→ The system automatically filters to only that meeting and retrieves up to 100 chunks

#### **Example 2: Ask About All Meetings**
```
User: "What meetings do I have available?"
```
→ The new "Manage Meetings" tab shows all meetings with metadata

#### **Example 3: Filter by Date (Future Enhancement)**
Currently, you can extend the filtering to support date ranges:

```python
# In src/agents/rag_service.py, add:
if "last week" in query_lower:
    return {
        "k": 20,
        "filter": {
            "meeting_date": {
                "$gte": "2025-11-26",
                "$lte": "2025-12-03"
            }
        }
    }
```

---

## New Features Added

### 1. **Enhanced PineconeManager** (`src/retrievers/pinecone.py`)

Added three new methods:

```python
# Delete by meeting ID
delete_by_meeting_id(meeting_id: str, namespace: str = "default")

# Delete entire namespace
delete_namespace(namespace: str)

# List all meetings with metadata
list_meetings(namespace: str = "default", limit: int = 100)
```

### 2. **New "Manage Meetings" Tab** in Gradio UI

- 📋 List all meetings in a table format
- 🗑️ Delete meetings by ID
- 🔄 Refresh to see latest data
- ⚠️ Safety warnings for permanent deletions

### 3. **Command-Line Utility** (`scripts/manage_pinecone.py`)

- `list` - Show all meetings
- `delete <meeting_id>` - Delete specific meeting
- `stats` - Show index statistics
- `clear` - Clear all data (with confirmation)

---

## Testing Your Metadata Filtering

### **Test 1: Verify Filtering Works**

1. Upload 2-3 different videos to create multiple meetings
2. Note the Meeting IDs (e.g., `meeting_abc12345`, `meeting_def67890`)
3. In chat, ask: `"Summarize meeting_abc12345"`
4. Verify the response only includes content from that specific meeting

### **Test 2: List All Meetings**

1. Go to "📊 Manage Meetings" tab
2. Click "🔄 Refresh Meeting List"
3. Verify you see all your uploaded meetings with:
   - Meeting ID
   - Title
   - Date
   - Participants

### **Test 3: Delete a Test Meeting**

1. Copy a Meeting ID from the list
2. Paste it in the "Meeting ID" field
3. Click "🗑️ Delete Meeting"
4. Refresh the list to confirm it's gone
5. Try querying that meeting in chat - should return no results

---

## Metadata Fields Available for Filtering

Your current implementation stores these metadata fields:

| Field | Type | Example | Filterable |
|-------|------|---------|------------|
| `meeting_id` | string | `meeting_abc12345` | ✅ Yes |
| `meeting_date` | string | `2025-12-03` | ✅ Yes |
| `title` | string | `Project Planning` | ✅ Yes |
| `speaker` | string | `John Doe` | ✅ Yes |
| `start_time` | float | `120.5` | ✅ Yes |
| `end_time` | float | `135.2` | ✅ Yes |
| `participants` | list | `["John", "Jane"]` | ✅ Yes |
| `source` | string | `video_upload` | ✅ Yes |

---

## Advanced Filtering Examples

### **Filter by Speaker**
```python
search_kwargs = {
    "k": 10,
    "filter": {"speaker": {"$eq": "John Doe"}}
}
```

### **Filter by Date Range**
```python
search_kwargs = {
    "k": 20,
    "filter": {
        "meeting_date": {
            "$gte": "2025-12-01",
            "$lte": "2025-12-03"
        }
    }
}
```

### **Filter by Multiple Criteria**
```python
search_kwargs = {
    "k": 15,
    "filter": {
        "$and": [
            {"meeting_date": {"$gte": "2025-12-01"}},
            {"speaker": {"$eq": "John Doe"}}
        ]
    }
}
```

---

## Summary

### ✅ **Question 1: Deleting Test Transcriptions**
- **3 methods available:** Gradio UI, CLI script, Python code
- **Recommended:** Use the new "Manage Meetings" tab in Gradio
- **Safety:** All methods include confirmations

### ✅ **Question 2: Metadata Filtering**
- **Already implemented** and working
- **Automatic filtering** when you mention a meeting ID
- **New UI tab** to visualize all meetings
- **Extensible** for date ranges, speakers, etc.

---

## Next Steps

1. **Test the new features:**
   ```bash
   python app_v4.py
   ```
   
2. **Navigate to "📊 Manage Meetings" tab** to see your meetings

3. **Try the CLI utility:**
   ```bash
   python scripts/manage_pinecone.py list
   ```

4. **Experiment with filtering** by asking specific meeting questions in chat

---

## Need Help?

- Check the Gradio UI tooltips and instructions
- Run `python scripts/manage_pinecone.py` for CLI help
- Review the code in `src/retrievers/pinecone.py` for API details
