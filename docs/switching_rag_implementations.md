# Switching Between RAG Implementations

This guide explains how to switch between the original RAG agent and the new LangGraph-based implementation.

## Quick Switch

Open `app.py` and find this section near the top:

```python
# ============================================================
# CONFIGURATION: Switch between RAG implementations
# ============================================================
USE_LANGGRAPH = False  # Set to True to use LangGraph implementation
```

**To use LangGraph:**
```python
USE_LANGGRAPH = True
```

**To use the original:**
```python
USE_LANGGRAPH = False
```

Then restart your Gradio app.

## How It Works

The configuration uses Python's dynamic imports:

```python
if USE_LANGGRAPH:
    from core.rag_agent_langgraph import RagAgentLangGraph as RagAgentService
    print("🔷 Using LangGraph-based RAG Agent")
else:
    from core.rag_agent_service import RagAgentService
    print("🔶 Using Original RAG Agent")
```

Both implementations have the **exact same interface**:
```python
def generate_response(message: str, history: List[List[str]]) -> Generator[str, None, None]
```

This means the rest of your application code doesn't need to change at all.

## Verifying Which Version Is Running

When you start the app, look for the console output:
- `🔷 Using LangGraph-based RAG Agent` = LangGraph version
- `🔶 Using Original RAG Agent` = Original version

## Differences Between Implementations

### Original (`rag_agent_service.py`)
- **Architecture**: Linear flow (retrieve → generate)
- **Pros**: Simple, straightforward, proven to work
- **Cons**: Harder to extend with new features

### LangGraph (`rag_agent_langgraph.py`)
- **Architecture**: State graph with explicit nodes (analyze → retrieve → generate)
- **Pros**: 
  - Better observability (can inspect state at each step)
  - Easier to extend (just add new nodes)
  - Built-in state management
  - Future-ready for advanced features
- **Cons**: 
  - Slightly more complex
  - Small overhead from state management

## Testing Checklist

After switching implementations, test:

1. ✅ **Basic query**: "What were the main topics discussed?"
2. ✅ **Follow-up question**: 
   - First: "What was discussed about marketing?"
   - Then: "Who was responsible for that?"
3. ✅ **Comprehensive query**: "Summarize the entire meeting"
4. ✅ **Streaming**: Verify responses stream smoothly
5. ✅ **Error handling**: Check graceful error messages

Both implementations should produce similar quality responses.

## Troubleshooting

### Import Error
If you see an import error when using LangGraph:
```bash
pip install 'langgraph>=0.2.0,<0.3.0'
```

### Dependency Conflict Warning
You may see a warning about `langgraph-prebuilt` requiring `langchain-core>=1.0.0`. This is safe to ignore as we're not using `langgraph-prebuilt` in our implementation.

### Different Responses
Both implementations use the same LLM and retrieval logic, so responses should be very similar. Small variations are normal due to LLM non-determinism.

## Rollback Plan

If LangGraph doesn't work as expected:

1. Set `USE_LANGGRAPH = False` in `app.py`
2. Restart the app
3. Everything returns to the working original version

The original `rag_agent_service.py` file is **completely untouched** and will always work.
