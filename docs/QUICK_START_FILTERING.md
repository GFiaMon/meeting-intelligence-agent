# Metadata Filtering - Quick Start Guide

## TL;DR - Answer to Your Question

**Your colleague is WRONG**: Pinecone **DOES** support metadata filtering, and it does it **BEFORE** similarity search (which is exactly what you want).

**Your implementation**: You ARE attempting to use metadata filtering in your code.

**The question**: Is it working correctly? Let's test it!

---

## How to Test (3 Simple Steps)

### Step 1: Check Your Current Data

Open a Python terminal in your project directory and run:

```python
from core.pinecone_manager import PineconeManager

# Connect to Pinecone
pm = PineconeManager()

# Check stats
stats = pm.index.describe_index_stats()
print(f"Total vectors: {stats.total_vector_count}")
print(f"Namespaces: {list(stats.namespaces.keys())}")

# Sample a vector to see metadata
from utils.embedding_utils import get_embedding_model
embeddings = get_embedding_model()

query_embedding = embeddings.embed_query("test")
response = pm.index.query(
    namespace="default",
    vector=query_embedding,
    top_k=1,
    include_metadata=True
)

if response.matches:
    print("\nSample metadata:")
    print(response.matches[0].metadata)
    
    # Check if meeting_id exists
    if "meeting_id" in response.matches[0].metadata:
        print("\n✅ meeting_id field EXISTS!")
        meeting_id = response.matches[0].metadata["meeting_id"]
        print(f"Sample meeting_id: {meeting_id}")
    else:
        print("\n❌ meeting_id field MISSING!")
```

**Expected output:**
- If you see `meeting_id` in the metadata → Good! Proceed to Step 2
- If you don't see `meeting_id` → Your documents don't have metadata yet. Upload a new meeting.

### Step 2: Test Filtering Directly

If Step 1 showed a `meeting_id`, test filtering:

```python
# Use the meeting_id from Step 1
meeting_id = "meeting_abc12345"  # Replace with actual value

# Test filter
filter_dict = {"meeting_id": meeting_id}

filtered_response = pm.index.query(
    namespace="default",
    vector=query_embedding,
    top_k=5,
    filter=filter_dict,
    include_metadata=True
)

print(f"\nResults with filter: {len(filtered_response.matches)}")

if filtered_response.matches:
    # Check if all results have correct meeting_id
    all_correct = all(
        m.metadata.get("meeting_id") == meeting_id 
        for m in filtered_response.matches
    )
    
    if all_correct:
        print("✅ FILTERING WORKS! All results from correct meeting.")
    else:
        print("❌ FILTERING BROKEN! Results from wrong meetings.")
        for m in filtered_response.matches:
            print(f"  - {m.metadata.get('meeting_id')}")
else:
    print("⚠️ No results (filter may be too restrictive)")
```

**Expected output:**
- `✅ FILTERING WORKS!` → Your filtering is working correctly!
- `❌ FILTERING BROKEN!` → There's an issue with filter implementation
- `⚠️ No results` → Filter syntax might be wrong

### Step 3: Test in Your RAG Agent

If Step 2 works, test your RAG agent:

```python
from core.rag_agent_langgraph import RagAgentLangGraph

agent = RagAgentLangGraph(pm)

# Test query with meeting_id
query = f"Summarize {meeting_id}"

# Check what search_kwargs are generated
kwargs = agent._get_retrieval_kwargs(query)
print(f"\nGenerated search_kwargs: {kwargs}")

# Should show something like:
# {'k': 100, 'filter': {'meeting_id': 'meeting_abc12345'}}

if "filter" in kwargs:
    print("✅ Agent IS generating filters!")
else:
    print("❌ Agent NOT generating filters!")
```

---

## What Each Result Means

### ✅ All Tests Pass
**Meaning:** Metadata filtering is working perfectly!

**What you can do:**
- Query specific meetings: "Summarize meeting_abc12345"
- Filter by date (add date filters to your code)
- Filter by speaker (already have speaker metadata)

### ⚠️ Step 1 Fails (No meeting_id)
**Meaning:** Your documents don't have metadata yet.

**Fix:**
1. Upload a new meeting transcript using your Gradio app
2. Check that `rag_pipeline.py` is adding metadata (it should be - I saw it in the code)
3. Run Step 1 again

### ❌ Step 2 Fails (Filter doesn't work)
**Meaning:** Pinecone isn't applying the filter correctly.

**Possible fixes:**

**Fix A: Try different filter syntax**
```python
# Try these different syntaxes:
filter_dict = {"meeting_id": meeting_id}  # Simple
# OR
filter_dict = {"meeting_id": {"$eq": meeting_id}}  # Explicit
```

**Fix B: Update LangChain**
```bash
pip install -U langchain-pinecone
```

**Fix C: Check Pinecone version**
```bash
pip install -U pinecone-client
```

### ❌ Step 3 Fails (Agent doesn't generate filters)
**Meaning:** Your `_get_retrieval_kwargs` method isn't detecting the meeting_id.

**Fix:** The regex in your code looks for `meeting_[a-f0-9]{8}`. Make sure your query includes the meeting_id in that exact format.

Example queries that WILL trigger filtering:
- "Summarize meeting_abc12345"
- "What was discussed in meeting_abc12345?"

Example queries that WON'T trigger filtering:
- "Summarize the meeting"
- "What was discussed?"

---

## Understanding Your Current Implementation

### Where Filtering Happens

1. **Query Analysis** (`_get_retrieval_kwargs` method):
   ```python
   # Detects meeting_id in query
   meeting_id_match = re.search(r'meeting_([a-f0-9]{8})', query)
   
   # If found, creates filter
   if meeting_id and is_comprehensive:
       return {
           "k": 100,
           "filter": {"meeting_id": {"$eq": meeting_id}}
       }
   ```

2. **Retrieval** (`get_retriever` method):
   ```python
   # Passes filter to Pinecone via LangChain
   retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
   ```

3. **Pinecone** (internal):
   - Filters vectors by metadata FIRST
   - Then does similarity search on filtered subset
   - Returns only matching vectors

### What Metadata You're Storing

From `rag_pipeline.py`, you're storing:
- `meeting_id` ✅ (for filtering by meeting)
- `meeting_date` ✅ (for filtering by date)
- `start_time`, `end_time` ✅ (for filtering by time in meeting)
- `speaker` ✅ (for filtering by speaker)
- `chunk_index`, `total_chunks` ✅ (for ordering)
- And more...

This is **excellent** metadata! You can filter by any of these fields.

---

## Advanced Filtering Examples

Once basic filtering works, you can do:

### Filter by Date Range
```python
{
    "meeting_date": {"$gte": "2025-11-01", "$lte": "2025-11-30"}
}
```

### Filter by Speaker
```python
{
    "meeting_id": "meeting_abc12345",
    "speaker": "SPEAKER_00"
}
```

### Filter by Time in Meeting
```python
{
    "meeting_id": "meeting_abc12345",
    "start_time": {"$gte": 60.0, "$lte": 300.0"}  # 1-5 minutes
}
```

### Combine Multiple Filters
```python
{
    "meeting_date": {"$gte": "2025-11-01"},
    "speaker": {"$in": ["SPEAKER_00", "SPEAKER_01"]},
    "chunk_type": "conversation_turn"
}
```

---

## Common Misconceptions About Pinecone Filtering

### ❌ Myth: "Pinecone doesn't support metadata filtering"
**✅ Truth:** Pinecone has robust metadata filtering with many operators ($eq, $ne, $gt, $lt, $in, etc.)

### ❌ Myth: "Filtering happens after similarity search"
**✅ Truth:** Pinecone does **pre-filtering** - filters BEFORE similarity search (more efficient!)

### ❌ Myth: "You can only filter by one field"
**✅ Truth:** You can filter by multiple fields with AND/OR logic

### ❌ Myth: "Filtering is slow"
**✅ Truth:** Pre-filtering can actually make queries FASTER by reducing search space

---

## Next Steps

1. ✅ Run the 3-step test above
2. ✅ If tests pass: Celebrate! Your filtering works!
3. ✅ If tests fail: Use the fixes provided
4. ✅ Read the full guide: `docs/METADATA_FILTERING_GUIDE.md`
5. ✅ Run comprehensive tests: `python tests/test_metadata_filtering.py`

---

## Quick Reference: Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| (implicit) | Equal to | `{"meeting_id": "meeting_001"}` |
| `$eq` | Equal to | `{"meeting_id": {"$eq": "meeting_001"}}` |
| `$ne` | Not equal | `{"speaker": {"$ne": "SPEAKER_00"}}` |
| `$gt` | Greater than | `{"start_time": {"$gt": 60.0}}` |
| `$gte` | Greater than or equal | `{"start_time": {"$gte": 60.0}}` |
| `$lt` | Less than | `{"end_time": {"$lt": 300.0}}` |
| `$lte` | Less than or equal | `{"end_time": {"$lte": 300.0}}` |
| `$in` | In array | `{"speaker": {"$in": ["SPEAKER_00", "SPEAKER_01"]}}` |
| `$nin` | Not in array | `{"speaker": {"$nin": ["SPEAKER_02"]}}` |

---

## Summary

**Your colleague's concern:** "Pinecone doesn't let you filter by metadata"

**The reality:** Pinecone has excellent metadata filtering that works BEFORE similarity search.

**Your implementation:** You're already using it! Just need to verify it's working.

**How to verify:** Run the 3-step test above (takes 2 minutes).

**If it works:** You're all set! Use it with confidence.

**If it doesn't work:** Use the fixes provided in this guide.

🚀 **Go test it now!**
