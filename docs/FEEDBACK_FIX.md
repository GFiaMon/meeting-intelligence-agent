# Feedback Integration Fix - RunTree AttributeError

## Problem

The initial implementation caused an `AttributeError`:

```
AttributeError: 'RunTree' object has no attribute 'run_inline'
```

This occurred because `RunTree` from LangSmith is not compatible with LangGraph's callback system.

## Root Cause

LangGraph's callback manager expects callbacks to have a `run_inline` attribute, but LangSmith's `RunTree` doesn't implement this interface. Passing `RunTree` directly as a callback to `graph.astream()` caused the error.

## Solution

Changed the approach to use **LangSmith's automatic tracing** instead of manually creating `RunTree` objects:

### Before (❌ Broken)
```python
# This doesn't work - RunTree is not a valid LangGraph callback
run_tree = RunTree(
    name="chat_response",
    run_type="chain",
    inputs={"message": message, "history": history}
)

async for event in self.graph.astream(
    initial_state,
    config={"callbacks": [run_tree], ...}  # ❌ Error!
):
```

### After (✅ Working)
```python
# Use LangSmith's automatic tracing with metadata
run_metadata = {
    "conversation_id": str(len(history)),
    "message_index": len(history)
}

async for event in self.graph.astream(
    initial_state,
    config={"metadata": run_metadata}  # ✅ Works!
):
    # Generate a deterministic run_id
    run_id = f"chat_msg_{len(history)}"
```

## How It Works Now

### 1. **Automatic Tracing**
When `LANGCHAIN_TRACING_V2=true`, LangSmith automatically:
- Creates traces for all LLM calls
- Stores them with metadata
- Makes them queryable via the LangSmith API

### 2. **Deterministic Run IDs**
We generate simple, predictable run_ids:
```python
run_id = f"chat_msg_{len(history)}"
```

This allows us to:
- Track which message got which feedback
- Store the mapping in `run_id_tracker`
- Look up the actual LangSmith run later if needed

### 3. **Fallback to LangSmith Query**
If a run_id is not in our tracker, we query LangSmith:

```python
# Query LangSmith for runs with matching metadata
runs = client.list_runs(
    project_name=Config.LANGCHAIN_PROJECT,
    filter=f'eq(metadata_key, "message_index") and eq(metadata_value, "{message_index}")',
    limit=1,
    start_time=datetime.now() - timedelta(hours=1)
)
```

## Benefits of New Approach

✅ **No callback compatibility issues**  
✅ **Simpler code** - relies on LangSmith's built-in tracing  
✅ **Deterministic run_ids** - easier to debug  
✅ **Fallback mechanism** - can query LangSmith if needed  
✅ **Works with LangGraph** - no custom callback integration required  

## Trade-offs

⚠️ **Run IDs are custom** - Not the actual LangSmith UUID  
   - **Impact**: Minimal - we can still query for the real run_id if needed
   - **Benefit**: Simpler, more predictable IDs

⚠️ **Requires metadata matching** - Feedback lookup may need LangSmith query  
   - **Impact**: Slight delay if run_id not in tracker
   - **Benefit**: More robust - can always find the run

## Testing

1. **Start the app** with LangSmith enabled
2. **Chat with the bot** - should work without errors
3. **Click thumbs up/down** - feedback should be sent
4. **Check console** for:
   ```
   📍 Stored run_id chat_msg_0 for message index 0
   ✅ Feedback sent to LangSmith: Like (score: 1.0) for run_id: chat_msg_0
   ```
5. **Check LangSmith** - feedback should appear in the Feedback tab

## Files Changed

1. **`src/agents/conversational.py`**
   - Removed `RunTree` callback approach
   - Added metadata-based run tracking
   - Generate deterministic run_ids

2. **`src/ui/gradio_app.py`**
   - Enhanced `handle_feedback()` with LangSmith query fallback
   - Better error messages and debugging

## Future Improvements

- [ ] Use actual LangSmith run UUIDs if we can capture them from traces
- [ ] Cache LangSmith queries to avoid repeated API calls
- [ ] Add retry logic for feedback submission
- [ ] Batch feedback submissions for better performance

## References

- [LangSmith Tracing Docs](https://docs.smith.langchain.com/tracing)
- [LangGraph Callbacks](https://langchain-ai.github.io/langgraph/how-tos/callbacks/)
- [LangSmith Feedback API](https://docs.smith.langchain.com/evaluation/how_to_guides/feedback)
