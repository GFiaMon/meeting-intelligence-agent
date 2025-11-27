# app.py
# Standard library imports
import os
import re
import uuid
from datetime import datetime

# Third-party library imports
import gradio as gr
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Local/custom imports
from config import Config
from core.pinecone_manager import PineconeManager
from core.rag_pipeline import process_transcript_to_documents
from core.transcription_service import TranscriptionService

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

def upload_to_pinecone(transcription_data, video_file):
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
        
        meeting_metadata = {
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "source_file": os.path.basename(video_file) if video_file else "unknown",
            "transcription_model": "whisperx-large-v2",
            "language": raw_data.get("language", "en")
        }
        
        # Process transcript with semantic grouping and rich metadata
        docs = process_transcript_to_documents(
            text, 
            segments, 
            meeting_id,
            meeting_metadata=meeting_metadata
        )
        
        pinecone_mgr.upsert_documents(docs, namespace="default")
        
        return f"✅ Successfully uploaded {len(docs)} documents to Pinecone! (ID: {meeting_id})\n📊 Avg chunk size: {sum(d.metadata['char_count'] for d in docs) // len(docs)} chars"
    except Exception as e:
        return f"❌ Error uploading: {str(e)}"

def chat_with_meetings(message, history):
    """Query stored meeting transcriptions using RAG with LangChain ConversationalRetrievalChain"""
    if not pinecone_available or not pinecone_mgr:
        return "❌ Pinecone service is not available. Please check your API key configuration."
    
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY
        )
        
        # Dynamic retrieval strategy based on query intent
        query_lower = message.lower()
        
        # Check for meeting_id in query (e.g., "meeting_abc12345")
        meeting_id_match = re.search(r'meeting_([a-f0-9]{8})', message)
        meeting_id = meeting_id_match.group(0) if meeting_id_match else None
        
        # Determine optimal k and filters based on query type
        comprehensive_keywords = ["summarize", "summary", "all", "entire", "complete", "overview", "everything", "full"]
        is_comprehensive = any(keyword in query_lower for keyword in comprehensive_keywords)
        
        if meeting_id and is_comprehensive:
            # Specific meeting summary - retrieve ALL chunks from that meeting
            search_kwargs = {
                "k": 100,  # High k to ensure we get all chunks
                "filter": {"meeting_id": {"$eq": meeting_id}}
            }
        elif is_comprehensive:
            # General comprehensive question - retrieve many chunks
            search_kwargs = {"k": 20}
        else:
            # Specific question - semantic search with moderate k
            search_kwargs = {"k": 5}
        
        # Get retriever with dynamic search parameters
        retriever = pinecone_mgr.get_retriever(
            namespace="default",
            search_kwargs=search_kwargs
        )
        
        # Create custom prompt template for meeting context
        prompt_template = """You are a helpful meeting assistant. Use the provided meeting transcript excerpts to answer questions accurately and concisely.

When answering:
- Reference specific speakers when relevant (e.g., "SPEAKER_00 mentioned...")
- Include timestamps if they help provide context
- If the context doesn't contain the answer, say so clearly
- Be conversational and natural

Context from meetings:
{context}

Question: {question}

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create memory and populate with history
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Add Gradio history to memory
        for user_msg, assistant_msg in history:
            if user_msg and assistant_msg:
                memory.chat_memory.add_user_message(user_msg)
                memory.chat_memory.add_ai_message(assistant_msg)
        
        # Create ConversationalRetrievalChain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": PROMPT},
            return_source_documents=True,
            verbose=False  # Set to True for debugging
        )
        
        # Run the chain
        result = chain({"question": message})
        
        return result["answer"]
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in chat_with_meetings: {error_details}")
        return f"❌ Error querying meetings: {str(e)}"

# --- Gradio Interface ---
with gr.Blocks(title="Meeting Agent - Diarization") as demo:
    transcription_state = gr.State()
    video_file_state = gr.State()  # Store video file path

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

    def transcribe_and_store_video(video_file, progress=gr.Progress()):
        """Wrapper to transcribe and store video file path."""
        result = transcribe_video_interface(video_file, progress)
        # Return transcription results + video file path for state
        return result[0], result[1], result[2], result[3], video_file

    transcribe_btn.click(
        fn=transcribe_and_store_video,
        inputs=video_input,
        outputs=[output_text, timing_info, transcription_state, upload_section, video_file_state]
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
            inputs=[transcription_state, video_file_state],
            outputs=[upload_status]
        )
    
    with gr.Tab("💬 Ask About Meetings"):
        gr.Markdown("### Ask questions about your stored meetings")
        gr.Markdown("**Powered by LangChain ConversationalRetrievalChain** - Natural language answers with conversation memory")
        gr.Markdown("Examples: 'What were the main action items?', 'Who mentioned the budget?', 'What decisions were made?'")
        
        # Use your existing chatbot interface
        chatbot = gr.ChatInterface(
            fn=chat_with_meetings,
            title="Meeting Q&A Assistant",
            description="Ask questions about your transcribed meetings. The AI uses RAG (Retrieval-Augmented Generation) to search through stored transcripts and provide natural language answers.",
            examples=[
                "What were the main action items from the meetings?",
                "Who was responsible for the marketing presentation?",
                "What was decided about the Q4 budget?",
                "Summarize the key discussion points"
            ]
        )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )