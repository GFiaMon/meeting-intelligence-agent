import gradio as gr
import torch

import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Import backend modules
from core.transcription import whisper_model, diarization_model, segment_formatter

import warnings
warnings.filterwarnings("ignore", message="torchaudio._backend.list_audio_backends has been deprecated")
# warnings.filterwarnings("ignore", message="Model was trained with.*Bad things might happen")
warnings.filterwarnings("ignore", message="std(): degrees of freedom is <= 0")

# Load environment variables
load_dotenv()

# # Load environment variables
# env_path = os.path.join(os.getcwd(), '.env')
# load_dotenv(dotenv_path=env_path, override=True)
# print(f"DEBUG: Loading .env from: {env_path}")

# Debug: Check if token is loaded
hf_token_debug = os.getenv("HUGGINGFACE_TOKEN")
print(f"DEBUG: HUGGINGFACE_TOKEN found: {'Yes' if hf_token_debug else 'No'}")

def process_video(video_file, progress=gr.Progress()):
    """
    Orchestrates the transcription and diarization process using backend modules.
    """
    try:
        if video_file is None:
            return "❌ Please upload a video file first", "⏱️ Waiting for file..."
        
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            return "❌ Hugging Face token required", "Create .env file with HUGGINGFACE_TOKEN=your_token"
        
        start_time = time.time()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Step 1: Transcription
        progress(0.1, desc="🎬 Transcribing audio...")
        transcript_result, audio = whisper_model.transcribe_audio(
            video_file, 
            device=device
        )
        
        # Step 2: Diarization
        progress(0.6, desc="👥 Identifying speakers...")
        diarized_segments = diarization_model.add_speaker_labels(
            audio, 
            transcript_result, 
            hf_token, 
            device=device
        )
        
        # Step 3: Formatting
        progress(0.9, desc="📝 Formatting results...")
        display_text, rag_segments = segment_formatter.format_to_display_and_rag(diarized_segments)
        
        # Generate timing info
        processing_time = time.time() - start_time
        timing_info = segment_formatter.generate_timing_info(diarized_segments, processing_time, video_file, device)
        
        return display_text, timing_info

    except Exception as e:
        return f"❌ Error: {str(e)}", "Check console for details"

# Gradio Interface
with gr.Blocks(title="Meeting Agent - Diarization") as demo:
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
    
    transcribe_btn.click(
        fn=process_video,
        inputs=video_input,
        outputs=[output_text, timing_info]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)