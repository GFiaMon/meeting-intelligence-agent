# Metadata Filtering Testing Guide

## Quick Answer to Your Question

**Your colleague is PARTIALLY CORRECT**: Pinecone DOES support metadata filtering, and your implementation IS attempting to use it. However, whether it's actually working depends on a few factors that we'll test.

**The Good News**: Pinecone performs **pre-filtering** (filters BEFORE similarity search), which is exactly what you need for meeting-specific queries.

**The Question**: Is your implementation correctly passing the filter to Pinecone? Let's find out!

---

## What You'll Learn

1. ✅ Whether metadata filtering is currently working in your agent
2. ✅ How Pinecone's metadata filtering actually works
3. ✅ How to test and verify filtering behavior
4. ✅ How to fix any issues if filtering isn't working

---

## Testing Steps

### Step 1: Read the Guide (5 minutes)

Read the comprehensive guide to understand how metadata filtering works:

```bash
cat docs/METADATA_FILTERING_GUIDE.md
```

This explains:
- How Pinecone's pre-filtering works
- What your current implementation does
- Potential issues to watch for

### Step 2: Run Quick Diagnostic (1 minute)

Check if your existing Pinecone data has the right metadata:

```bash
python tests/diagnose_filtering.py
```

This will:
- ✅ Connect to your Pinecone index
- ✅ Show what metadata fields exist
- ✅ Test a simple filter query
- ✅ Tell you if filtering is working

**Expected Output:**
- If working: "🎉 METADATA FILTERING IS WORKING!"
- If not working: Specific error messages and recommendations

### Step 3: Run Full Test Suite (2 minutes)

Run comprehensive tests with synthetic data:

```bash
python tests/test_metadata_filtering.py
```

This will:
- ✅ Create test documents with different meeting_ids
- ✅ Upload them to Pinecone (in test namespace)
- ✅ Test multiple filter syntaxes
- ✅ Test direct Pinecone API
- ✅ Test LangChain integration
- ✅ Test RAG agent behavior

**Expected Output:**
- Detailed test results for each filter syntax
- Final verdict: PASS/FAIL for each test
- Recommendations for fixes if needed

### Step 4: Test in Your App (Manual)

If tests pass, try these queries in your Gradio app:

1. **Without filter** (should search all meetings):
   ```
   "What were the main topics discussed?"
   ```

2. **With filter** (should search only one meeting):
   ```
   "Summarize meeting_abc12345"
   ```
   Replace `meeting_abc12345` with an actual meeting_id from your data.

3. **Verify results**:
   - Check if the response only mentions content from the specified meeting
   - Check if multiple meetings are mentioned (indicates filter not working)

---

## Understanding the Results

### ✅ If Tests PASS

**What it means:**
- Metadata filtering is working correctly
- Your RAG agent can filter by meeting_id
- Queries like "Summarize meeting_abc12345" will only retrieve chunks from that meeting

**What to do:**
- Use your agent with confidence!
- Try queries with specific meeting_ids
- Consider adding more metadata filters (date ranges, speakers, etc.)

### ⚠️ If Tests PARTIALLY PASS

**What it means:**
- Some filter syntaxes work, others don't
- You may need to adjust your filter format

**What to do:**
- Use the filter syntax that passed
- Update your `_get_retrieval_kwargs` method to use the working syntax
- See "How to Fix" section below

### ❌ If Tests FAIL

**What it means:**
- Metadata filtering is not working
- Filters are not being applied to Pinecone queries
- All queries search across all meetings

**What to do:**
- Check Pinecone and LangChain versions
- Verify metadata is being stored (Step 2 diagnostic)
- See "How to Fix" section below

---

## How to Fix Common Issues

### Issue 1: No meeting_id in Metadata

**Symptom:** Diagnostic shows no meeting_id field

**Fix:**
1. Check `core/rag_pipeline.py` - ensure metadata includes meeting_id
2. Re-upload a meeting transcript
3. Run diagnostic again

### Issue 2: Filter Not Being Applied

**Symptom:** Tests show results from multiple meetings

**Possible causes:**
1. **Wrong filter syntax** - Try different syntax from test results
2. **LangChain version** - Update to latest: `pip install -U langchain-pinecone`
3. **Filter not passed correctly** - Check `pinecone_manager.py`

**Fix for filter syntax:**

In `core/rag_agent_service.py` and `core/rag_agent_langgraph.py`, change line ~19:

```python
# FROM:
"filter": {"meeting_id": {"$eq": meeting_id}}

# TO (simpler syntax):
"filter": {"meeting_id": meeting_id}
```

### Issue 3: Retriever Not Using Filter

**Symptom:** Direct Pinecone query works, but LangChain retriever doesn't

**Fix:**

Check `core/pinecone_manager.py` line 69-83. Ensure filter is passed correctly:

```python
def get_retriever(self, namespace, search_kwargs=None):
    if search_kwargs is None:
        search_kwargs = {"k": 5}
    
    vectorstore = PineconeVectorStore(
        index_name=self.index_name,
        embedding=self.embeddings,
        namespace=namespace,
        pinecone_api_key=self.api_key
    )
    
    # This should pass search_kwargs (including filter) to retriever
    return vectorstore.as_retriever(search_kwargs=search_kwargs)
```

---

## Advanced: Adding More Filters

Once basic filtering works, you can add more sophisticated filters:

### Filter by Date Range

```python
"filter": {
    "meeting_id": meeting_id,
    "meeting_date": {"$gte": "2025-11-01", "$lte": "2025-11-30"}
}
```

### Filter by Speaker

```python
"filter": {
    "meeting_id": meeting_id,
    "speaker": "SPEAKER_00"
}
```

### Filter by Time Range in Meeting

```python
"filter": {
    "meeting_id": meeting_id,
    "start_time": {"$gte": 60.0, "$lte": 300.0}  # Between 1-5 minutes
}
```

---

## Pinecone Filter Operators

Pinecone supports these filter operators:

- `$eq`: Equal to (can be implicit)
- `$ne`: Not equal to
- `$gt`: Greater than
- `$gte`: Greater than or equal to
- `$lt`: Less than
- `$lte`: Less than or equal to
- `$in`: In array
- `$nin`: Not in array

**Examples:**

```python
# Simple equality (implicit $eq)
{"meeting_id": "meeting_abc12345"}

# Explicit equality
{"meeting_id": {"$eq": "meeting_abc12345"}}

# Greater than
{"start_time": {"$gt": 60.0}}

# In array
{"speaker": {"$in": ["SPEAKER_00", "SPEAKER_01"]}}

# Multiple conditions (AND)
{
    "meeting_id": "meeting_abc12345",
    "speaker": "SPEAKER_00"
}
```

---

## FAQ

### Q: Does Pinecone filter BEFORE or AFTER similarity search?

**A:** Pinecone filters BEFORE similarity search (pre-filtering). This is efficient and correct for your use case.

### Q: Will filtering make queries slower?

**A:** No! Pre-filtering can actually make queries faster by reducing the search space.

### Q: Can I filter by multiple fields?

**A:** Yes! You can combine multiple metadata fields in one filter (they're combined with AND logic).

### Q: What if I want OR logic?

**A:** Pinecone supports `$or` operator:
```python
{
    "$or": [
        {"meeting_id": "meeting_001"},
        {"meeting_id": "meeting_002"}
    ]
}
```

### Q: How do I know what meeting_ids exist?

**A:** You can query Pinecone without a filter and collect unique meeting_ids from results, or maintain a separate database/list of meeting_ids.

---

## Next Steps

1. ✅ Run `python tests/diagnose_filtering.py`
2. ✅ Run `python tests/test_metadata_filtering.py`
3. ✅ Review test results
4. ✅ Fix any issues using this guide
5. ✅ Test in Gradio app with real queries
6. ✅ Celebrate! 🎉

---

## Need Help?

If tests fail and you can't figure out why:

1. Check Pinecone documentation: https://docs.pinecone.io/docs/metadata-filtering
2. Check LangChain documentation: https://python.langchain.com/docs/integrations/vectorstores/pinecone
3. Share test output for debugging

---

## Summary

**Your colleague's concern:** "Pinecone doesn't let you filter by metadata"

**The truth:** Pinecone DOES support metadata filtering, and it's very powerful!

**Your implementation:** Attempts to use filtering, but we need to test if it's working correctly.

**These tests will tell you:** Definitively whether filtering is working and how to fix it if not.

Run the tests and you'll have your answer! 🚀
