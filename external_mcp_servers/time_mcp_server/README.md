# Berlin Time & World Time MCP Servers

This directory contains two example MCP (Model Context Protocol) servers built with Gradio.

## 📂 Available Servers

### 1. Simple Berlin Time (`app_time_mcp_server.py`)
- **Function:** Returns current time in Berlin.
- **Complexity:** Simple, no parameters.
- **Port:** 7860
- **Best for:** Learning the basics of MCP.

### 2. World Time (`app_world_time_mcp_server.py`)
- **Function:** Returns current time for 25+ major cities.
- **Complexity:** Takes a `city` parameter (e.g., "Tokyo", "New York").
- **Port:** 7860 (when deployed) / 7861 (local dev).
- **Best for:** Demonstrating tool arguments and dynamic responses.

---

## 🚀 Local Testing

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server of your choice:

**Option A: Berlin Time**
```bash
python app_time_mcp_server.py
# Runs on http://localhost:7860
```

**Option B: World Time**
```bash
python app_world_time_mcp_server.py
# Runs on http://localhost:7861 (to avoid conflict)
```

3. Open the URL in your browser to test the UI manually.

---

## ☁️ Deploying to HuggingFace Spaces

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose **Gradio** as the SDK.
3. Upload your files.

### ⚠️ IMPORTANT: Deployment Checklist

#### 1. Configure the Entry File (The "Pro" Way)
Instead of renaming your file to `app.py`, you can tell HuggingFace which file to run by editing the **YAML Header** at the very top of your `README.md` in the Space.

**For Berlin Time:**
```yaml
---
title: Berlin Time MCP
emoji: 🕐
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.0.0
app_file: app_time_mcp_server.py  <-- CHANGE THIS
pinned: false
---
```

**For World Time:**
```yaml
---
title: World Time MCP
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.0.0
app_file: app_world_time_mcp_server.py  <-- CHANGE THIS
pinned: false
---
```

#### 2. Check the Port
HuggingFace Spaces **REQUIRES** the app to run on port **7860**.
- If you use `app_world_time_mcp_server.py`, **change `server_port=7861` to `server_port=7860`** in the code before deploying.
- If you don't do this, you will get an `OSError: Cannot find empty port`.

### Configuration for Your Agent

Once deployed, update your `src/config/settings.py`:

```python
servers["berlin_time"] = {
    "url": "https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME/gradio_api/mcp/sse",
    "transport": "sse"
}
```

**Note:** The URL must end with `/sse`.

---

## 📚 Documentation

- [Step-by-Step Guide](STEP_BY_STEP_GUIDE.md): Detailed teaching guide.
- [MCP Connection Flow](../.gemini/antigravity/brain/26cb67ea-9995-44cc-8251-52a912873dc8/mcp_connection_flow.md): Visual diagram of how it works.
