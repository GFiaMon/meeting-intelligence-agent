# Step-by-Step Guide: Building & Deploying MCP Servers

## ✅ What We've Built

You now have **two** working MCP server examples in `external_mcp_servers/`:

1. **`app_time_mcp_server.py`** (Original)
   - Simple, parameter-less tool.
   - Returns Berlin time only.
   - Great for first-time understanding.

2. **`app_world_time_mcp_server.py`** (Upgraded)
   - Accepts a `city` parameter.
   - Returns time for 25+ cities.
   - Demonstrates how LLMs pass arguments to tools.

---

## 📚 Understanding the Components

### 1. The Core Function

**Simple (Berlin):**
```python
def get_berlin_time():
    # No arguments needed
    return {"time": "..."}
```

**Advanced (World):**
```python
def get_time_for_city(city: str = "Berlin"):
    # Takes an argument!
    # LLM will send: {"city": "Tokyo"}
    return {"city": "Tokyo", "time": "..."}
```

### 2. The Gradio Interface

```python
demo = gr.Interface(
    fn=get_time_for_city,
    inputs=gr.Textbox(...),  # Defines input schema for MCP
    outputs=gr.JSON(...),
    api_name="get_time_for_city"
)
```

### 3. The MCP Magic

```python
demo.launch(mcp_server=True)
```
This single line turns your web app into an AI tool server!

---

## 🚀 Deploying to HuggingFace Spaces (Critical Details)

Deploying is easy, but there are **two common pitfalls** to watch out for.

### Step 1: Configure the Entry File

You don't need to rename your file to `app.py`! You can tell HuggingFace which file to run.

1. Go to your Space's **Files** tab.
2. Click on `README.md` to edit it.
3. Look at the **YAML Header** (the metadata at the top between `---`).
4. Change the `app_file` line:

**For Berlin Time:**
```yaml
app_file: app_time_mcp_server.py
```

**For World Time:**
```yaml
app_file: app_world_time_mcp_server.py
```

This is much cleaner than renaming files!

### Step 2: ⚠️ Check the Port Number

**This is the most common error!**

HuggingFace Spaces **must** run on port **7860**.

- `app_time_mcp_server.py` is already set to 7860. ✅
- `app_world_time_mcp_server.py` is set to **7861** (for local testing). ❌

**You MUST change this line in `app.py` before deploying:**

```python
# CHANGE THIS:
server_port=7861

# TO THIS:
server_port=7860
```

If you forget this, you will see: `OSError: Cannot find empty port`.

### Step 3: Upload to Spaces

1. Create a new Space (SDK: **Gradio**).
2. Upload:
   - `app.py` (your chosen server)
   - `requirements.txt`
3. Wait for "Running" status.

---

## 🔗 Connecting Your Agent

Once deployed, your agent needs to know where to look.

### Update `src/config/settings.py`

```python
servers["berlin_time"] = {
    # 1. Use your Space URL (MUST end with /sse)
    # Format: https://huggingface.co/spaces/USERNAME/SPACE_NAME/gradio_api/mcp/sse
    "url": "https://gfiamon-date-time-mpc-server-tool.hf.space/gradio_api/mcp/sse",
    
    # OR for Local Testing (use 127.0.0.1 and /sse)
    # "url": "http://127.0.0.1:7870/gradio_api/mcp/sse",
    
    # 2. Use 'sse' transport (Server-Sent Events)
    "transport": "sse"
}
```

**CRITICAL:** You **MUST** append `/sse` to the end of the URL. If you forget this, the connection will hang!

### How It Works

1. **Agent Starts:** Connects to that URL via SSE.
2. **Discovery:** Asks "What tools do you have?"
3. **World Time:** Server replies "I have `get_time_for_city` which takes a `city` string".
### Switching Between Servers

If you want to use the **World Time** server (which allows choosing a city), just update your `settings.py`:

```python
        # 2. World Time MCP Server (Remote HF Space)
        servers["world_time"] = {
            "url": "https://gfiamon-date-time-mpc-server-tool.hf.space/gradio_api/mcp/sse",
            "transport": "sse"
        }
```

The agent will automatically discover the new `get_time_for_city` tool next time it starts!

---

## 🎓 Teaching This to Colleagues

**Key Teaching Points:**

1. **One Codebase, Two Interfaces:**
   - **Humans** use the Web UI (click buttons).
   - **AI Agents** use the MCP API (hidden endpoint).
   - Both are powered by the *same Python function*.

2. **Deployment Simplicity:**
   - No Docker, no Nginx, no complex config.
   - Just `app.py` + `requirements.txt` on HF Spaces.

3. **The "Port Trap":**
   - Remind them: Local dev can use any port, but HF Spaces enforces port 7860.

4. **Dynamic Discovery:**
   - Show them how you can update the tool on HF (e.g., add "Mars Time"), restart the agent, and it *instantly* knows about the new feature without changing agent code.
