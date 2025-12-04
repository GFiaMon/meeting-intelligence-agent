import sys
import os
# Add project root to path to allow running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import os
import gradio as gr
from fastapi import Request, FastAPI
import uvicorn
from contextlib import asynccontextmanager
import hashlib
import hmac
import asyncio
import json

from src.zoom_mcp.zoom_client import ZoomRTMSClient
from src.zoom_mcp.processor import ZoomProcessor
from src.config.settings import Config

# Global state
zoom_client = None
processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global zoom_client, processor
    processor = ZoomProcessor()
    zoom_client = ZoomRTMSClient(on_message=processor.process_message)
    yield
    # Shutdown
    if zoom_client:
        zoom_client.stop()
    if processor:
        await processor.close()

# Create FastAPI app explicitly to mount Gradio and Webhooks
app = FastAPI(lifespan=lifespan)

# --- Tool Definitions (Standard Python Functions) ---

async def start_listening(meeting_id: str):
    """
    Connects to the Zoom RTMS stream for the specified meeting ID.
    
    Args:
        meeting_id: The ID of the Zoom meeting to listen to.
    """
    global zoom_client
    if not zoom_client:
        return "Error: Zoom client not initialized."
    
    if zoom_client.is_running:
        return "Already listening to a meeting. Stop current stream first."

    # Start connection in background task
    asyncio.create_task(zoom_client.connect(meeting_id))
    return f"Started listening to meeting {meeting_id}"

async def stop_listening():
    """
    Stops the current Zoom RTMS stream.
    """
    global zoom_client
    if zoom_client:
        zoom_client.stop()
        return "Stopped listening."
    return "Client was not running."

async def get_status():
    """
    Returns the current status of the Zoom connection.
    """
    global zoom_client
    if zoom_client and zoom_client.is_running:
        return "🟢 Connected and listening"
    return "🔴 Disconnected"

# --- Webhook Endpoint for Zoom Validation ---

async def handle_zoom_webhook(request: Request):
    """
    Shared handler for Zoom Webhook validation and events.
    """
    try:
        # Log raw request details for debugging
        headers = dict(request.headers)
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        
        print(f"\n� [WEBHOOK RECEIVED]")
        print(f"Headers: {headers}")
        print(f"Body: {body_str}")
        
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            print("❌ Failed to decode JSON body")
            return {"status": "error", "message": "Invalid JSON"}

        event_type = data.get("event")
        print(f"� Event Type: {event_type}")
        
        # 1. URL Validation Challenge
        if event_type == "endpoint.url_validation":
            plain_token = data["payload"]["plainToken"]
            # Use Webhook Secret if available, otherwise fall back to Client Secret
            secret = Config.ZOOM_WEBHOOK_SECRET or Config.ZOOM_CLIENT_SECRET
            
            print(f"🔑 Plain Token: {plain_token}")
            
            if not secret:
                print("❌ CRITICAL: No ZOOM_WEBHOOK_SECRET or ZOOM_CLIENT_SECRET found!")
                return {"status": "error", "message": "Missing secrets"}

            # Hash the plainToken using HMAC-SHA256
            hash_object = hmac.new(
                secret.encode("utf-8"),
                plain_token.encode("utf-8"),
                hashlib.sha256
            )
            encrypted_token = hash_object.hexdigest()
            
            response_data = {
                "plainToken": plain_token,
                "encryptedToken": encrypted_token
            }
            
            print(f"✅ Validation Response: {response_data}")
            
            # Return with explicit JSON response and headers
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=response_data,
                status_code=200,
                headers={
                    "Content-Type": "application/json"
                }
            )
            
        # 2. Handle RTMS Started Event (The Real Trigger)
        if event_type == "meeting.rtms_started":
            print(f"🚀 RTMS Started! Extracting connection details...")
            payload = data.get("payload", {}).get("object", {})
            meeting_id = payload.get("id")
            
            print(f"📦 RTMS Payload Object: {payload}")
            
            # Assuming standard structure:
            # Note: Zoom documentation says it's in payload.object.rtms
            rtms_info = payload.get("rtms", {})
            signaling_url = rtms_info.get("url")
            token = rtms_info.get("token")
            
            if signaling_url and token:
                print(f"✅ Found RTMS URL and Token.")
                print(f"   URL: {signaling_url}")
                print(f"   Token: {token[:10]}... (truncated)")
                asyncio.create_task(zoom_client.connect_to_stream(signaling_url, token, str(meeting_id)))
            else:
                print("❌ Could not find 'url' or 'token' in RTMS payload.")
                print(f"   Available keys in rtms object: {list(rtms_info.keys())}")

        # 3. Handle other events
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# Zoom sends validation to both / and /webhook, so we handle both
@app.post("/webhook")
async def zoom_webhook(request: Request):
    """Handle Zoom Webhook at /webhook endpoint."""
    return await handle_zoom_webhook(request)

@app.post("/")
async def zoom_webhook_root(request: Request):
    """Handle Zoom Webhook at root endpoint (Zoom sometimes sends here too)."""
    return await handle_zoom_webhook(request)


# --- Gradio UI & MCP Server ---

# Global log buffer for UI
log_buffer = []

def add_log(message: str):
    """Add a message to the log buffer."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry) # Print to console
    log_buffer.append(log_entry)
    # Keep last 20 logs
    if len(log_buffer) > 20:
        log_buffer.pop(0)

def get_logs():
    """Get current logs as a string."""
    return "\n".join(reversed(log_buffer))

with gr.Blocks(title="Zoom RTMS Debugger") as demo:
    gr.Markdown("# 🐞 Zoom RTMS Debugger")
    gr.Markdown("Use this dashboard to monitor incoming webhooks and connection status.")
    
    with gr.Row():
        status_output = gr.Textbox(label="Connection Status", value="Disconnected", interactive=False)
        refresh_btn = gr.Button("Refresh Status")
        
    log_output = gr.TextArea(label="Live Logs (Webhooks & Events)", interactive=False, lines=20)
    
    # Auto-refresh logs every 2 seconds
    timer = gr.Timer(2)
    
    # Event handlers
    refresh_btn.click(get_status, outputs=status_output)
    timer.tick(get_logs, outputs=log_output)
    
    # Also update logs when status is refreshed
    refresh_btn.click(get_logs, outputs=log_output)

# Mount Gradio app
app = gr.mount_gradio_app(app, demo, path="/", mcp_server=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
