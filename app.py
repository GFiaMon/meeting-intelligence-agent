"""
app_v4.py - Conversational Meeting Intelligence Interface

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
from src.config.settings import Config
from src.retrievers.pinecone import PineconeManager
from src.processing.transcription import TranscriptionService
from src.agents.conversational import ConversationalMeetingAgent
from src.ui.gradio_app import create_demo

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
# LAUNCH APPLICATION
# ============================================================

if __name__ == "__main__":
    if not agent:
        print("❌ Cannot launch - Agent initialization failed")
        print("Please check your Pinecone API key configuration")
    else:
        print("🚀 Launching Conversational Meeting Intelligence Interface...")
        
        # Create the demo using the initialized agent
        demo = create_demo(agent)
        
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True
        )
