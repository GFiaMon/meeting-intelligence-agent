# app.py
# Standard library imports
import os
import uuid
from datetime import datetime

# Third-party library imports
import gradio as gr

# Local/custom imports
from config import Config
from core.pinecone_manager import PineconeManager
from core.rag_pipeline import process_transcript_to_documents
from core.transcription_service import TranscriptionService

# ============================================================
# CONFIGURATION: Switch between RAG implementations
# ============================================================
USE_LANGGRAPH = True  # Set to True to use LangGraph implementation

if USE_LANGGRAPH:
    from core.rag_agent_langgraph import RagAgentLangGraph as RagAgentService
    print("🔷 Using LangGraph-based RAG Agent")
else:
    from core.rag_agent_service import RagAgentService
    print("🔶 Using Original RAG Agent")
# ============================================================

# Initialize services
transcription_svc = TranscriptionService()
try:
    pinecone_mgr = PineconeManager()
    pinecone_available = True
    # Initialize RAG Agent Service
    rag_agent = RagAgentService(pinecone_mgr)
except Exception as e:
    print(f"Warning: Pinecone not available: {e}")
    pinecone_mgr = None
    pinecone_available = False
    rag_agent = None

def transcribe_video_interface(video_file, progress=gr.Progress()):
    """Clean interface - no business logic"""
    try:
        progress(0.2, desc="🔄 Processing...")
        
        # Call service layer
        result = transcription_svc.transcribe_video(video_file, progress_callback=progress)
        
        progress(1.0, desc="✅ Complete!")
        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}", "Failed", None, gr.Group(visible=False)
            
        return result["transcription"], result["timing_info"], gr.Group(visible=True)
        
    except Exception as e:
        return f"Error: {str(e)}", "Failed", None, gr.Group(visible=False)

def upload_to_pinecone_interface(transcription, timing_info, video_file):
    """Interface for uploading to Pinecone"""
    if not pinecone_available or not pinecone_mgr:
        return "❌ Pinecone service is not available. Please check your API key configuration."
    
    if not transcription:
        return "⚠️ No transcription to upload. Please transcribe a video first."
        
    try:
        # Generate a unique meeting ID
        meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        meeting_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create metadata
        meeting_metadata = {
            "meeting_id": meeting_id,
            "date": meeting_date,
            "source": "video_upload",
            "title": f"Meeting {meeting_date}",
            "source_file": os.path.basename(video_file) if video_file else "unknown",
            "transcription_model": "whisperx-large-v2",
            "language": timing_info.get("language", "en") # Assuming timing_info contains raw_data
        }
        
        # Process and upload
        docs = process_transcript_to_documents(
            transcription, 
            timing_info.get("segments", []), # Assuming timing_info contains raw_data with segments
            meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        pinecone_mgr.upsert_documents(docs, namespace="default")
        
        return f"✅ Successfully uploaded {len(docs)} documents to Pinecone! (ID: {meeting_id})\n📊 Avg chunk size: {sum(d.metadata['char_count'] for d in docs) // len(docs)} chars"
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error uploading to Pinecone: {error_details}")
        return f"❌ Error uploading: {str(e)}"

# def chat_with_meetings(message, history):
#     """
#     Query stored meeting transcriptions using the RagAgentService.
#     Yields "thinking" status updates and then the final response.
#     """
#     if not rag_agent:
#         # When type="messages", we must return a list of messages
#         from gradio import ChatMessage
#         yield [ChatMessage(role="assistant", content="❌ RAG Agent service is not available. Please check your configuration.")]
#         return
    
#     # Delegate to the service generator
#     # Gradio ChatInterface supports generators for streaming
#     try:
#         # Note: When type="messages", history is passed as a list of ChatMessage objects
#         for response_chunk in rag_agent.generate_response(message, history):
#             yield response_chunk
            
#     except Exception as e:
#         import traceback
#         error_details = traceback.format_exc()
#         print(f"Error in chat_with_meetings: {error_details}")
#         from gradio import ChatMessage
#         yield [ChatMessage(role="assistant", content=f"❌ Error in chat service: {str(e)}")]

def chat_with_meetings(message, history):
    """
    Query stored meeting transcriptions using the RagAgentService.
    Yields streaming responses.
    """
    if not rag_agent:
        yield "❌ RAG Agent service is not available."
        return
    
    # Delegate to the service generator - it now yields strings directly
    try:
        for response_chunk in rag_agent.generate_response(message, history):
            yield response_chunk
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in chat_with_meetings: {error_details}")
        yield f"❌ Error in chat service: {str(e)}"

# --- Gradio Interface ---

# ============================================================
# TAB 1: Video Transcription & Upload Interface
# ============================================================
with gr.Blocks() as transcription_interface:
    transcription_text_state = gr.State() # Stores the transcription text
    transcription_timing_state = gr.State() # Stores the timing_info dictionary
    video_file_state = gr.State()  # Store video file path

    gr.Markdown("# 📹 Video Transcription & Storage")
    gr.Markdown("Upload your **Zoom** MP4 to identify who said what, then store it in Pinecone for AI-powered Q&A.")
    
    with gr.Row():
        with gr.Column():
            video_input = gr.Video(
                label="📹 Upload Zoom Video",
                sources=["upload", "webcam"],
                include_audio=True,
            )
            
            transcribe_btn = gr.Button("🎬 Transcribe with Speakers", variant="primary", size="lg")
            
        with gr.Column():
            output_text = gr.Textbox(
                label="📄 Speaker Transcription",
                lines=18,
                value="Transcription will appear here..."
            )
            
            timing_info = gr.Markdown(
                label="⏱️ Processing Info"
            )

    upload_section = gr.Group(visible=False)

    def transcribe_and_store_video(video_file, progress=gr.Progress()):
        """Wrapper to transcribe and store video file path."""
        # result contains: transcription, timing_info, group_update
        transcription, timing, group_update = transcribe_video_interface(video_file, progress)
        
        # We need to format timing info for the Markdown output
        timing_md = f"### ⏱️ Timing\n- Duration: {timing.get('duration', 'N/A')}s\n- Language: {timing.get('language', 'N/A')}"
        
        return transcription, timing_md, transcription, timing, group_update, video_file

    transcribe_btn.click(
        fn=transcribe_and_store_video,
        inputs=video_input,
        outputs=[
            output_text,                # Textbox
            timing_info,                # Markdown
            transcription_text_state,   # State (Text)
            transcription_timing_state, # State (Dict)
            upload_section,             # Group
            video_file_state            # State (File path)
        ]
    )
    
    with upload_section:
        gr.Markdown("### 📦 Store Transcription in Pinecone")
        upload_status = gr.Textbox(
            label="Storage Status",
            value="Transcribe a video first...",
            interactive=False
        )
        upload_btn = gr.Button("💾 Upload to Pinecone", variant="secondary", size="lg")
        
        upload_btn.click(
            fn=upload_to_pinecone_interface,
            inputs=[transcription_text_state, transcription_timing_state, video_file_state],
            outputs=[upload_status]
        )

# ============================================================
# TAB 2: Chatbot Interface
# ============================================================
with gr.Blocks() as chatbot_interface:
    gr.Markdown("# 💬 Ask About Your Meetings")
    gr.Markdown("**Powered by LangChain ConversationalRetrievalChain** - Natural language answers with conversation memory")
    gr.Markdown("💡 **Examples:** 'What were the main action items?', 'Who mentioned the budget?', 'What decisions were made?'")
    
    # Use your existing chatbot interface
    chatbot = gr.ChatInterface(
        fn=chat_with_meetings,
        # type="messages",  # Removed: causing TypeError in Gradio 6.0.1
        title="Meeting Q&A Assistant",
        description="Ask questions about your transcribed meetings. The AI uses RAG (Retrieval-Augmented Generation) to search through stored transcripts and provide natural language answers.",
        examples=[
            "What were the main action items from the meetings?",
            "Who was responsible for the marketing presentation?",
            "What was decided about the Q4 budget?",
            "Summarize the key discussion points"
        ]
    )

# ============================================================
# Combine interfaces using TabbedInterface
# ============================================================
demo = gr.TabbedInterface(
    interface_list=[transcription_interface, chatbot_interface],
    tab_names=["📹 Video Transcription", "💬 Ask About Meetings"],
    title="🎬 Meeting Intelligence Agent"
)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )