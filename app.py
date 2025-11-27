# app.py
import gradio as gr
from core.transcription_service import TranscriptionService
from core.pinecone_manager import PineconeManager
from core.rag_pipeline import process_transcript_to_documents
import uuid

# Initialize services
transcription_svc = TranscriptionService()
try:
    pinecone_mgr = PineconeManager()
    pinecone_available = True
except Exception as e:
    print(f"Warning: Pinecone not available: {e}")
    pinecone_mgr = None
    pinecone_available = False

def transcribe_video_interface(video_file, progress=gr.Progress()):
    """Clean interface - no business logic"""
    try:
        progress(0.2, desc="🔄 Processing...")
        
        # Call service layer
        result = transcription_svc.transcribe_video(video_file, progress_callback=progress)
        
        progress(1.0, desc="✅ Complete!")
        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}", "Failed", None, gr.Group(visible=False)
            
        return result["transcription"], result["timing_info"], result, gr.Group(visible=True)
        
    except Exception as e:
        return f"Error: {str(e)}", "Failed", None, gr.Group(visible=False)

def upload_to_pinecone(transcription_data):
    if not pinecone_available or not pinecone_mgr:
        return "❌ Pinecone service is not available. Check your API key."
        
    if not transcription_data:
        return "❌ No transcription data found. Please transcribe a video first."
        
    try:
        text = transcription_data.get("transcription", "")
        raw_data = transcription_data.get("raw_data", {})
        segments = raw_data.get("segments", [])
        
        # Generate a unique meeting ID
        meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        
        docs = process_transcript_to_documents(text, segments, meeting_id)
        pinecone_mgr.upsert_documents(docs, namespace="default")
        
        return f"✅ Successfully uploaded {len(docs)} documents to Pinecone! (ID: {meeting_id})"
    except Exception as e:
        return f"❌ Error uploading: {str(e)}"

def chat_with_meetings(message, history):
    """Query stored meeting transcriptions using RAG"""
    if not pinecone_available or not pinecone_mgr:
        return "❌ Pinecone service is not available. Please check your API key configuration."
    
    try:
        # Get retriever for the default namespace
        retriever = pinecone_mgr.get_retriever(namespace="default", search_kwargs={"k": 3})
        
        # Retrieve relevant documents
        docs = retriever.get_relevant_documents(message)
        
        if not docs:
            return "No relevant information found in stored meetings. Please make sure you have uploaded transcriptions."
        
        # Format context from retrieved documents
        context = "\n\n".join([f"Context {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
        
        # Simple response (you can integrate with OpenAI/LangChain for better responses)
        response = f"Based on the meeting transcripts, here's what I found:\n\n{context}"
        
        return response
        
    except Exception as e:
        return f"❌ Error querying meetings: {str(e)}"




# --- Gradio Interface ---
with gr.Blocks(title="Meeting Agent - Diarization") as demo:
    transcription_state = gr.State()

    gr.Markdown("# 🎬 Meeting Agent: Video Speaker Diarization")
    gr.Markdown("Upload your **Zoom** MP4 to identify who said what.")
    
    with gr.Row():
        with gr.Column():
            video_input = gr.Video(
                label="📹 Upload Zoom Video",
                sources=["upload", "webcam"],
                include_audio=True,
            )
            
            transcribe_btn = gr.Button("🎬 Transcribe with Speakers", variant="primary")
            
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

    transcribe_btn.click(
        fn=transcribe_video_interface,
        inputs=video_input,
        outputs=[output_text, timing_info, transcription_state, upload_section]
    )
    with upload_section:
        gr.Markdown("### 📦 Store Transcription")
        upload_status = gr.Textbox(
            label="Storage Status",
            value="Transcribe a video first...",
            interactive=False
        )
        upload_btn = gr.Button("💾 Upload to Pinecone", variant="secondary")
        
        upload_btn.click(
            fn=upload_to_pinecone,
            inputs=[transcription_state],
            outputs=[upload_status]
        )
    
    with gr.Tab("💬 Ask About Meetings"):
        gr.Markdown("### Ask questions about your stored meetings")
        gr.Markdown("Examples: 'What were the main action items?', 'Who mentioned the budget?', 'What decisions were made?'")
        
        # Use your existing chatbot interface
        chatbot = gr.ChatInterface(
            fn=chat_with_meetings,
            title="Meeting Q&A Assistant",
            description="Ask questions about your transcribed meetings. The AI will search through stored transcripts to provide accurate answers.",
            examples=[
                "What were the main action items from the meetings?",
                "Who was responsible for the marketing presentation?",
                "What was decided about the Q4 budget?"
            ]
        )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )