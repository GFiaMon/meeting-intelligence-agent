# Human-in-the-Loop Feedback Integration with LangSmith

## Overview

This document explains how the chatbot integrates user feedback (thumbs up/down) with LangSmith for tracking user satisfaction and improving the AI agent.

## Features

- 👍👎 **Thumbs Up/Down Icons**: Users can provide feedback on each AI response
- 📊 **LangSmith Integration**: Feedback is automatically sent to LangSmith for tracking
- 🔍 **Run Tracking**: Each AI response is associated with a unique `run_id` for precise feedback attribution

## How It Works

### 1. Gradio Chatbot Configuration

The `gr.Chatbot` component is configured with `feedback_options`:

```python
custom_chatbot = gr.Chatbot(
    height="70vh",
    show_label=False,
    feedback_options=("Like", "Dislike")  # Enables thumbs up/down icons
)
```

**Note**: The exact strings `"Like"` and `"Dislike"` (case-sensitive) are required for Gradio to render them as thumb icons.

### 2. Feedback Event Listener

The `.like()` event is wired to a handler function:

```python
custom_chatbot.like(
    fn=handle_feedback,
    inputs=None,
    outputs=None
)
```

### 3. Run ID Tracking

Each AI response generates a LangSmith `run_id` that is:
- Captured using LangSmith's `RunTree` callback
- Stored in a dictionary mapping message index to run_id
- Used to associate feedback with the specific AI interaction

```python
run_id_tracker: Dict[int, str] = {}
```

### 4. Feedback Submission to LangSmith

When a user clicks thumbs up/down:

```python
def handle_feedback(like_data: gr.LikeData):
    message_index = like_data.index
    feedback_value = like_data.value  # "Like" or "Dislike"
    run_id = run_id_tracker.get(message_index)
    
    # Convert to score
    score = 1.0 if feedback_value == "Like" else 0.0
    
    # Send to LangSmith
    client.create_feedback(
        run_id=run_id,
        key="user_feedback",
        score=score,
        comment=f"User {'liked' if feedback_value == 'Like' else 'disliked'} this response"
    )
```

## LangSmith Configuration

### Prerequisites

1. **Enable LangSmith Tracing** in your `.env` file:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=meeting-agent
```

2. **Verify Configuration** - Check that settings are loaded:

```python
from src.config.settings import Config

print(f"Tracing enabled: {Config.LANGCHAIN_TRACING_V2}")
print(f"Project: {Config.LANGCHAIN_PROJECT}")
```

### Viewing Feedback in LangSmith

1. Go to [LangSmith](https://smith.langchain.com/)
2. Navigate to your project (e.g., "meeting-agent")
3. Click on any run/trace
4. Go to the **"Feedback"** tab
5. You should see:
   - **Key**: `user_feedback`
   - **Score**: `1.0` (Like) or `0.0` (Dislike)
   - **Comment**: User feedback description

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (Gradio)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Chatbot with feedback_options=("Like", "Dislike")     │ │
│  │  👍 👎 icons appear next to each AI message            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ User clicks thumbs
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    handle_feedback()                         │
│  1. Get message index from like_data.index                   │
│  2. Get feedback value ("Like" or "Dislike")                 │
│  3. Lookup run_id from run_id_tracker[index]                 │
│  4. Convert to score (1.0 or 0.0)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Send feedback
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangSmith Client                          │
│  client.create_feedback(                                     │
│      run_id=run_id,                                          │
│      key="user_feedback",                                    │
│      score=score,                                            │
│      comment="User liked/disliked this response"             │
│  )                                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Stored in LangSmith
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangSmith Platform                        │
│  - Feedback tab shows all user ratings                       │
│  - Can filter by score, date, run_id                         │
│  - Analyze patterns in user satisfaction                     │
└─────────────────────────────────────────────────────────────┘
```

## Code Flow

### Agent Response Generation

```python
async def generate_response(self, message: str, history: List[List[str]]):
    # Create RunTree to track this conversation
    run_tree = RunTree(
        name="chat_response",
        run_type="chain",
        inputs={"message": message, "history": history}
    )
    
    # Stream response with callbacks
    async for event in self.graph.astream(
        initial_state,
        config={"callbacks": [run_tree], ...}
    ):
        # ... process events ...
        
        # When final response is ready
        if final_response:
            run_id = str(run_tree.id)
            run_tree.end(outputs={"response": final_response})
            run_tree.post()  # Send to LangSmith
            
            # Return response with run_id
            yield (final_response, run_id)
```

### UI Handler

```python
async def chat_with_agent(message, history):
    message_index = len(history)
    
    async for response_data in agent.generate_response(text, tuple_history):
        if isinstance(response_data, tuple):
            response_chunk, run_id = response_data
            if run_id:
                run_id_tracker[message_index] = run_id
            yield response_chunk
```

## Troubleshooting

### Feedback Not Appearing in LangSmith

**Check 1**: Verify LangSmith is enabled
```python
from src.config.settings import Config
print(Config.LANGCHAIN_TRACING_V2)  # Should be "true"
print(Config.LANGCHAIN_API_KEY)     # Should be your API key
```

**Check 2**: Check console logs
```bash
# Look for these messages:
✅ Feedback sent to LangSmith: Like (score: 1.0) for run_id: xxx
📍 Stored run_id xxx for message index 0
```

**Check 3**: Verify run_id is captured
```python
# In the console, you should see:
📍 Stored run_id abc123... for message index 0
```

### No run_id Found

If you see `⚠️ No run_id found for message index X`:

1. Ensure LangSmith tracing is enabled
2. Check that `RunTree` is being created properly
3. Verify the agent is posting runs to LangSmith

### Thumbs Not Appearing

If thumbs up/down icons don't show:

1. Verify `feedback_options=("Like", "Dislike")` (exact case)
2. Check Gradio version (requires Gradio 4.0+)
3. Try refreshing the browser

## Best Practices

1. **Monitor Feedback Regularly**: Check LangSmith dashboard weekly
2. **Analyze Patterns**: Look for common issues in disliked responses
3. **Iterate on Prompts**: Use feedback to improve system prompts
4. **Track Metrics**: Monitor feedback score trends over time

## Future Enhancements

- [ ] Add custom feedback options (e.g., "Helpful", "Not Helpful", "Inaccurate")
- [ ] Implement feedback comments (allow users to explain why)
- [ ] Create feedback analytics dashboard
- [ ] Auto-flag low-scoring responses for review
- [ ] A/B test different prompts based on feedback

## References

- [Gradio Chatbot Documentation](https://www.gradio.app/docs/gradio/chatbot)
- [LangSmith Feedback API](https://docs.smith.langchain.com/)
- [LangChain Callbacks](https://python.langchain.com/docs/modules/callbacks/)
