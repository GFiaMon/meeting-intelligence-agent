import os
import random
import uuid
from datetime import datetime
from typing import Dict, Any

import gradio as gr

from src.config.settings import Config
from src.processing.metadata_extractor import MetadataExtractor
from src.retrievers.pinecone import PineconeManager
from src.retrievers.pipeline import process_transcript_to_documents
from src.tools.video import get_video_state, reset_video_state, _video_state

def create_demo(agent):
    """
    Create the Gradio interface for the Meeting Intelligence Assistant.
    Multi-page app with Chat and Edit Transcript tabs.
    
    Args:
        agent: Initialized ConversationalMeetingAgent instance
        
    Returns:
        gr.Blocks: The Gradio demo application
    """
    
    # ============================================================
    # SHARED STATE FOR CROSS-TAB COMMUNICATION
    # ============================================================
    
    # This state tracks when a transcript is uploaded from the Edit tab
    # so the Chat tab can acknowledge it
    upload_notification = {
        "has_new_upload": False,
        "meeting_id": None,
        "doc_count": 0
    }
    
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

    async def chat_with_agent(message: Dict[str, Any], history):
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
            # Check if there's a new upload notification from Edit tab
            if upload_notification["has_new_upload"]:
                meeting_id = upload_notification["meeting_id"]
                doc_count = upload_notification["doc_count"]
                
                # Acknowledge the upload
                yield f"""✅ **I see you've uploaded your edited transcript!**

**Meeting ID:** `{meeting_id}`
**Documents Created:** {doc_count}

Great! Your meeting is now stored in Pinecone. What would you like to know about it?

You can ask me to:
- Summarize the meeting
- Extract action items
- Find specific discussions
- Or ask any question about the content!
"""
                
                # Clear the notification
                upload_notification["has_new_upload"] = False
                upload_notification["meeting_id"] = None
                upload_notification["doc_count"] = 0
                return
            
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
            
            # Delegate to agent (async generator)
            async for response_chunk in agent.generate_response(text, tuple_history):
                yield response_chunk
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in chat_with_agent: {error_details}")
            yield f"❌ Error: {str(e)}"

    # ============================================================
    # EDIT TRANSCRIPT FUNCTIONS
    # ============================================================

    def load_transcript_for_editing():
        """Load the current transcription from video state."""
        video_state = get_video_state()
        transcript = video_state.get("transcription_text", "")
        
        if not transcript:
            return "", "⚠️ No transcription available. Please transcribe a video first in the Chat tab."
        
        # The transcript already includes the summary header from metadata extraction
        # Just return it as-is
        return transcript, "✅ Transcription loaded with metadata. Make your edits below and click 'Save & Upload to Pinecone'."

    def save_and_upload_transcript(edited_text):
        """Save edited transcript and upload to Pinecone."""
        if not edited_text or not edited_text.strip():
            return "❌ Cannot upload empty transcription.", edited_text
        
        try:
            # Update the video state with edited text
            _video_state["transcription_text"] = edited_text
            
            # Get video state
            video_state = get_video_state()
            
            # Initialize Pinecone manager
            pinecone_mgr = PineconeManager()
            
            # ---------------------------------------------------------
            # INTELLIGENT METADATA EXTRACTION
            # ---------------------------------------------------------
            try:
                extractor = MetadataExtractor()
                
                print("🧠 Extracting intelligent metadata (title, summary, date)...")
                extracted_data = extractor.extract_metadata(edited_text)
                
                # Apply speaker mapping if found
                if extracted_data.get("speaker_mapping"):
                    print(f"👥 Applying speaker mapping: {extracted_data['speaker_mapping']}")
                    edited_text = extractor.apply_speaker_mapping(edited_text, extracted_data["speaker_mapping"])
                    # Update the editor with the mapped text so the user sees it? 
                    # For now, we just save it to Pinecone.
            except Exception as e:
                print(f"⚠️ Metadata extraction failed: {e}")
                extracted_data = {}

            # Generate unique meeting ID
            meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
            
            # Use extracted date if available, else today
            meeting_date = extracted_data.get("meeting_date") or datetime.now().strftime("%Y-%m-%d")
            
            # Create comprehensive metadata with consistent field names
            video_filename = os.path.basename(video_state["uploaded_video_path"]) if video_state.get("uploaded_video_path") else "edited_transcript"
            
            meeting_metadata = {
                "meeting_id": meeting_id,
                "meeting_date": meeting_date,  # ✅ Fixed: was "date"
                "date_transcribed": datetime.now().strftime("%Y-%m-%d"),
                "source": "video_upload_edited",
                "meeting_title": extracted_data.get("title", f"Meeting {meeting_date}"),  # ✅ Fixed: was "title"
                "summary": extracted_data.get("summary", "No summary available."),  # ✅ Added to metadata
                "speaker_mapping": extracted_data.get("speaker_mapping", {}),  # ✅ Added speaker mapping
                "source_file": video_filename,
                "transcription_model": Config.WHISPER_MODEL,
                "language": "en"
            }
            
            # Process transcription into documents
            segments = video_state.get("transcription_segments", [])
            
            # Calculate duration and format as MM:SS
            total_duration_seconds = segments[-1]["end"] if segments else 0
            minutes = int(total_duration_seconds // 60)
            seconds = int(total_duration_seconds % 60)
            formatted_duration = f"{minutes:02d}:{seconds:02d}"
            
            docs = process_transcript_to_documents(
                edited_text,
                segments,
                meeting_id,
                meeting_metadata=meeting_metadata
            )
            
            # Update metadata with formatted duration
            meeting_metadata["duration"] = formatted_duration
            
            # Re-process documents to ensure metadata is included in all chunks
            # (Or just update the docs directly since they are mutable)
            for doc in docs:
                doc.metadata["duration"] = formatted_duration

            
            # Upload to Pinecone
            pinecone_mgr.upsert_documents(docs)
            
            # Calculate statistics
            avg_chunk_size = sum(d.metadata['char_count'] for d in docs) // len(docs) if docs else 0
            
            # Reset state after successful upload
            reset_video_state()
            
            # Set notification for Chat tab
            upload_notification["has_new_upload"] = True
            upload_notification["meeting_id"] = meeting_id
            upload_notification["doc_count"] = len(docs)
            
            result = f"""✅ Successfully uploaded to Pinecone!

**Meeting ID:** `{meeting_id}`
**Documents Created:** {len(docs)}
**Average Chunk Size:** {avg_chunk_size} characters
**Date:** {meeting_date}

---

**🎉 Next Step:** Go to the **💬 Chat** tab and send any message (or just say "hi") to continue!

The agent will acknowledge your upload and help you analyze the meeting.
"""
            
            return result, ""  # Clear the editor after successful upload
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in save_and_upload_transcript: {error_details}")
            return f"❌ Error uploading to Pinecone: {str(e)}", edited_text

    # ============================================================
    # MANAGE MEETINGS FUNCTIONS
    # ============================================================
    
    def list_all_meetings():
        """List all meetings stored in Pinecone with metadata."""
        try:
            pinecone_mgr = PineconeManager()
            meetings = pinecone_mgr.list_meetings(limit=1000)
            
            if not meetings:
                return "📭 No meetings found in Pinecone.", ""
            
            # Format meetings as a table
            table_md = f"## 📋 Found {len(meetings)} Meeting(s)\n\n"
            table_md += "| # | Meeting ID | Title | Date | Duration | Source File |\n"
            table_md += "|---|------------|-------|------|----------|-------------|\n"
            
            for i, meeting in enumerate(meetings, 1):
                meeting_id = meeting.get('meeting_id', 'N/A')
                title = meeting.get('title', 'Untitled')
                date = meeting.get('meeting_date', 'N/A')
                duration = meeting.get('duration', 'N/A')
                source_file = meeting.get('source_file', 'N/A')
                
                table_md += f"| {i} | `{meeting_id}` | {title} | {date} | {duration} | {source_file} |\n"
            
            table_md += "\n\n**💡 Tip:** Copy a Meeting ID from above to delete it below."
            
            return table_md, ""
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error listing meetings: {error_details}")
            return f"❌ Error: {str(e)}", ""
    
    def delete_meeting_by_id(meeting_id: str):
        """Mock delete function that directs users to the admin."""
        if not meeting_id or not meeting_id.strip():
            return "❌ Please enter a valid Meeting ID."
        
        return "⚠️ Please contact the admin to help you with that: [Guillermo](https://github.com/GFiaMon/meeting-intelligence-agent)"


    # ============================================================
    # GRADIO UI - MULTI-PAGE APP
    # ============================================================

    with gr.Blocks(title="Meeting Intelligence Assistant", fill_height=True) as demo:
        
        # Main Title
        gr.Markdown("""
        # 💬 Meeting Intelligence Assistant
        **Upload videos, transcribe, edit, and search your meeting recordings**
        """)
        
        # Create tabs for multi-page navigation
        with gr.Tabs():
            
            # ========================================
            # TAB 1: CHAT INTERFACE
            # ========================================
            with gr.Tab("💬 Chat", id="chat_tab"):
                
                with gr.Accordion("ℹ️ Features & Instructions", open=False):
                    gr.Markdown("""
                    **Features:**
                    - 📹 Upload meeting videos directly in chat (drag & drop or click 📎)
                    - 🎤 Automatic transcription with speaker identification
                    - ✏️ View / Edit transcriptions in the "Edit Transcript" tab
                    - 💾 Store in Pinecone for AI-powered search
                    - 🔍 Ask questions about your meetings
                    - 📊 Extract action items and summaries
                    
                    **Get started:** Say "Hi" or upload a video file!
                    """)
                
                # Custom Chatbot with responsive height
                custom_chatbot = gr.Chatbot(
                    height="70vh",
                    show_label=False
                )
                
                # Define a pool of diverse example questions
                all_examples = [
                    "Summarize the key decisions from the last meeting",
                    "What are the action items assigned to me?",
                    "List all meetings from October",
                    "Find discussions about 'budget' and 'costs'",
                    "What did John say about the deadline?",
                    "Draft a follow-up email based on this meeting",
                    "Create a Notion page with these meeting minutes",
                    "What are the main risks identified in the project?",
                    "Compare the progress reported in the last two meetings",
                    "Who attended the 'Strategy Review' meeting?",
                    "Extract all dates and deadlines mentioned",
                    "Summarize the feedback on the new design",
                    "What are the next steps for the marketing team?",
                    "Did we decide on a launch date?",
                    "Upload this transcript to Notion"
                ]
                
                # Select 5 random examples (changes on app restart)
                selected_examples = random.sample(all_examples, 5)
                # Format for gr.Examples (needs list of lists)
                formatted_examples = [[ex] for ex in selected_examples]
                
                # Multimodal chat interface
                chat_interface = gr.ChatInterface(
                    fn=chat_with_agent,
                    chatbot=custom_chatbot,
                    multimodal=True,
                    title="",
                    description="",
                    cache_examples=False,
                    fill_height=True
                )
                
                # Persistent examples below the chat
                gr.Examples(
                    examples=formatted_examples,
                    inputs=[chat_interface.textbox],
                    label="📝 Try these examples (click to populate):"
                )
                
                gr.Markdown("""
                **💡 Tip:** After transcription completes, you can **view the full transcript** and make edits in the **"✏️ Edit Transcript"** tab before uploading to Pinecone!
                
                **🗑️ Memory Tip:** If you delete a meeting or want to start fresh, click the **Trash Icon** (Clear) above the chat to flush the agent's memory.
                """)
            
            # ========================================
            # TAB 2: EDIT TRANSCRIPT
            # ========================================
            with gr.Tab("✏️ Edit Transcript", id="edit_tab"):
                
                gr.Markdown("""
                ## View & Edit Your Transcription
                
                After transcribing a video in the Chat tab, you can **view the complete transcript** and make edits here before uploading to Pinecone.
                
                **Instructions:**
                1. Click "Load Transcript" to load the latest transcription
                2. Make your edits in the text box below
                3. Click "Save & Upload to Pinecone" when done
                """)
                
                with gr.Row():
                    load_btn = gr.Button("🔄 Load Transcript", variant="secondary", size="lg")
                
                status_msg = gr.Markdown("")
                
                transcript_editor = gr.Textbox(
                    label="Transcription",
                    placeholder="Click 'Load Transcript' to load the latest transcription...",
                    lines=20,
                    max_lines=30,
                    show_label=True
                )
                
                with gr.Row():
                    save_upload_btn = gr.Button("💾 Save & Upload to Pinecone", variant="primary", size="lg")
                
                upload_result = gr.Markdown("")
                
                # Event handlers
                load_btn.click(
                    fn=load_transcript_for_editing,
                    inputs=[],
                    outputs=[transcript_editor, status_msg]
                )
                
                save_upload_btn.click(
                    fn=save_and_upload_transcript,
                    inputs=[transcript_editor],
                    outputs=[upload_result, transcript_editor]
                )
                
                gr.Markdown("""
                ---
                **Note:** The transcription will be automatically cleared after successful upload.
                """)
            
            # ========================================
            # TAB 3: MANAGE MEETINGS
            # ========================================
            with gr.Tab("📊 Manage Meetings", id="manage_tab"):
                
                gr.Markdown("""
                ## Manage Your Stored Meetings
                
                View all meetings stored in Pinecone and delete test data or unwanted transcriptions.
                
                **Features:**
                - 📋 List all meetings with metadata (ID, title, date, participants)
                - 🗑️ Delete specific meetings by ID
                - 🔍 Filter and search through your meeting database
                """)
                
                # List meetings section
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh Meeting List", variant="secondary", size="lg")
                
                meetings_display = gr.Markdown("Click 'Refresh Meeting List' to see all stored meetings.")
                
                gr.Markdown("---")
                
                # Delete meeting section
                gr.Markdown("""
                ### 🗑️ Delete a Meeting
                
                Enter a Meeting ID from the list above to permanently delete it from Pinecone.
                """)
                
                with gr.Row():
                    meeting_id_input = gr.Textbox(
                        label="Meeting ID",
                        placeholder="e.g., meeting_abc12345",
                        scale=3
                    )
                    delete_btn = gr.Button("🗑️ Delete Meeting", variant="stop", size="lg", scale=1)
                
                delete_result = gr.Markdown("")
                
                # Event handlers
                refresh_btn.click(
                    fn=list_all_meetings,
                    inputs=[],
                    outputs=[meetings_display, delete_result]
                )
                
                delete_btn.click(
                    fn=delete_meeting_by_id,
                    inputs=[meeting_id_input],
                    outputs=[delete_result]
                )
                
                gr.Markdown("""
                ---
                **⚠️ Warning:** Deletion is permanent and cannot be undone!
                
                **💡 Tips:**
                - Use this to clean up test transcriptions
                - Meeting IDs are automatically generated when you upload videos
                - You can filter meetings by asking the chatbot: "What meetings do I have from last week?"
                """)

        
        # Footer (outside tabs, always visible)
        gr.Markdown("""
        ---
        """)
        with gr.Accordion("💡 Tips", open=False):
            gr.Markdown("""
        ---
        
        - Click the 📎 button or drag & drop to upload video files
        - Supported formats: MP4, AVI, MOV
        - Transcription includes automatic speaker identification
        - Use the "Edit Transcript" tab to make corrections before uploading
        - Ask specific questions to get better search results
        """)
        
        gr.Markdown("""
        <div style="text-align: center; margin-top: 2rem; padding-bottom: 2rem; border-top: 1px solid #E5E7EB; padding-top: 2rem;">
            <p style="font-size: 1.1em; margin-bottom: 1rem;">
                Made with ❤️ by <a href="https://github.com/GFiaMon" target="_blank" style="color: #2563EB; text-decoration: none; font-weight: bold;">Guillermo</a>
            </p>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
                <a href="https://github.com/GFiaMon/meeting-intelligence-agent" target="_blank" style="text-decoration: none; color: #374151; display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background-color: #F3F4F6; border-radius: 0.5rem; transition: background-color 0.2s;">
                    <span style="font-size: 1.2rem;">📦</span> GitHub Repo
                </a>
                <a href="https://www.linkedin.com/" target="_blank" style="text-decoration: none; color: #0077b5; display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background-color: #EFF6FF; border-radius: 0.5rem; transition: background-color 0.2s;">
                    <span style="font-size: 1.2rem;">�</span> LinkedIn
                </a>
            </div>
            <p style="font-size: 0.85em; color: #6B7280;">
                Powered by <strong>WhisperX</strong> • <strong>OpenAI</strong> • <strong>Pinecone</strong> • <strong>LangGraph</strong>
            </p>
        </div>
        """)

    return demo
