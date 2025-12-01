"""
app_experiment_3.py - Conversational Meeting Intelligence Interface

A chatbot-driven interface where all meeting intelligence functionality
is controlled through natural conversation with an AI agent.

Features:
- Multimodal chat interface (text + file uploads)
- Conversational video upload and transcription
- Transcription editing capabilities
- Pinecone storage integration
- Meeting query and analysis
"""

import os
import gradio as gr
from typing import Generator, Dict, Any

# Local imports
from config import Config
from core.pinecone_manager import PineconeManager
from core.transcription_service import TranscriptionService
from core.conversational_agent import ConversationalMeetingAgent

# ============================================================
# SERVICE INITIALIZATION
# ============================================================

print("🚀 Initializing Conversational Meeting Intelligence Agent...")

# Initialize services
transcription_svc = TranscriptionService()

try:
    pinecone_mgr = PineconeManager()
    pinecone_available = True
    print("✅ Pinecone service initialized")
except Exception as e:
    print(f"⚠️  Warning: Pinecone not available: {e}")
    pinecone_mgr = None
    pinecone_available = False

# Initialize conversational agent
if pinecone_available:
    agent = ConversationalMeetingAgent(pinecone_mgr, transcription_svc)
    print("✅ Conversational agent initialized")
else:
    agent = None
    print("❌ Agent initialization failed - Pinecone required")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_text_from_multimodal(content):
    """Extract text from Gradio 6.0 multimodal content format."""
    if isinstance(content, str):
        return content, []
    elif isinstance(content, dict):
        # Multimodal format: {"text": "...", "files": [...]}
        return content.get("text", ""), content.get("files", [])
    elif isinstance(content, list):
        # Alternative format: list of {text, type} objects
        text_parts = [item["text"] for item in content if item.get("type") == "text"]
        return " ".join(text_parts) if text_parts else "", []
    return str(content), []

def convert_to_tuple_history(messages_history):
    """Convert Gradio 6.0 messages format to tuple format for agent."""
    
    def extract_text_content(content):
        """Extract text from any Gradio content format."""
        text, _ = extract_text_from_multimodal(content)
        return text
    
    tuple_history = []
    i = 0
    while i < len(messages_history):
        msg = messages_history[i]
        if msg["role"] == "user":
            user_msg = extract_text_content(msg["content"])
            # Look for corresponding assistant message
            assistant_msg = None
            if i + 1 < len(messages_history) and messages_history[i + 1]["role"] == "assistant":
                assistant_msg = extract_text_content(messages_history[i + 1]["content"])
                i += 2
            else:
                i += 1
            tuple_history.append([user_msg, assistant_msg])
        else:
            i += 1
    return tuple_history

# ============================================================
# CHAT INTERFACE FUNCTION
# ============================================================

def chat_with_agent(message: Dict[str, Any], history):
    """
    Main chat function for multimodal interface.
    
    Args:
        message: Dict with "text" and "files" keys (multimodal format)
        history: Conversation history in Gradio messages format
        
    Yields:
        Agent's response chunks
    """
    if not agent:
        yield "❌ Agent service is not available. Please check Pinecone configuration."
        return
    
    try:
        # Extract text and files from multimodal message
        if isinstance(message, dict):
            text = message.get("text", "")
            files = message.get("files", [])
        else:
            # Fallback for non-multimodal
            text = str(message)
            files = []
        
        # If files are uploaded, process them
        if files:
            # Get the first video file
            video_file = files[0] if files else None
            if video_file:
                filename = os.path.basename(video_file)
                # Inject video path into message for agent
                text = f"Please transcribe my uploaded video: {video_file}"
                # Show user-friendly message
                yield f"📹 Processing video: **{filename}**\n\nStarting transcription..."
        
        if not text:
            yield "Please provide a message or upload a video file."
            return
        
        # Convert history to tuple format for agent
        tuple_history = convert_to_tuple_history(history) if history else []
        
        # Delegate to agent
        for response_chunk in agent.generate_response(text, tuple_history):
            yield response_chunk
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in chat_with_agent: {error_details}")
        yield f"❌ Error: {str(e)}"

# ============================================================
# GRADIO UI
# ============================================================

with gr.Blocks(title="Meeting Intelligence Assistant", fill_height=True) as demo:
    
    gr.Markdown("""
    # 💬 Meeting Intelligence Assistant
    
    **Upload videos and chat with your AI assistant to manage meeting recordings**
    
    **Features:**
    - 📹 Upload meeting videos directly in chat (drag & drop or click 📎)
    - 🎤 Automatic transcription with speaker identification
    - ✏️ Edit transcriptions before storing
    - 💾 Store in Pinecone for AI-powered search
    - 🔍 Ask questions about your meetings
    - 📊 Extract action items and summaries
    
    **Get started:** Say "Hi" or upload a video file!
    """)
    
    # Multimodal chat interface
    chat_interface = gr.ChatInterface(
        fn=chat_with_agent,
        multimodal=True,
        title="",
        description="",
        examples=[
            {"text": "Hi! What can you help me with?"},
            {"text": "What meetings do I have available?"},
            {"text": "Summarize the key decisions from my last meeting"},
            {"text": "Find all discussions about the project timeline"}
        ],
        cache_examples=False,
        fill_height=True
    )
    
    # Footer
    gr.Markdown("""
    ---
    
    **💡 Tips:**
    - Click the 📎 button or drag & drop to upload video files
    - Supported formats: MP4, AVI, MOV
    - Transcription includes automatic speaker identification
    - You can edit transcriptions before storing them
    - Ask specific questions to get better search results
    
    **🔧 Powered by:** WhisperX • OpenAI • Pinecone • LangGraph
    """)

# ============================================================
# LAUNCH APPLICATION
# ============================================================

if __name__ == "__main__":
    if not agent:
        print("❌ Cannot launch - Agent initialization failed")
        print("Please check your Pinecone API key configuration")
    else:
        print("🚀 Launching Conversational Meeting Intelligence Interface...")
        demo.launch(
            server_name="0.0.0.0",
            server_port=7862,
            share=False
        )
