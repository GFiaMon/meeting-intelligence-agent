# v3_fixed_diarization.py - CORRECT IMPORTS
import gradio as gr
import whisperx
import gc
# CORRECT WAY: Import DiarizationPipeline at point of use
from whisperx.diarize import DiarizationPipeline
# from pyannote.audio import Pipeline


import torch

import time
from datetime import datetime
import os
from dotenv import load_dotenv

import warnings
warnings.filterwarnings("ignore", message="torchaudio._backend.list_audio_backends has been deprecated")
# warnings.filterwarnings("ignore", message="Model was trained with.*Bad things might happen")
warnings.filterwarnings("ignore", message="std(): degrees of freedom is <= 0")

# Load environment variables
load_dotenv()

class FixedDiarizationV3:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.batch_size = 16
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        
        print(f"🚀 Configuration:")
        print(f"   Device: {self.device}")
        print(f"   HF Token: {'✅ Found' if self.hf_token else '❌ Missing'}")
    
    def transcribe_video_with_speakers(self, video_file, progress=gr.Progress()):
        """Correct WhisperX diarization pipeline"""
        try:
            if video_file is None:
                return "❌ Please upload a video file first", "⏱️ Waiting for file..."
            
            if not self.hf_token:
                return "❌ Hugging Face token required", "Create .env file with HUGGINGFACE_TOKEN=your_token"
            
            start_time = time.time()
            
            # ======================
            # STEP 1: Load Audio from Video
            # ======================
            progress(0.1, desc="🎬 Loading audio from video...")
            print("1️⃣ Loading audio directly from video...")
            
            audio = whisperx.load_audio(video_file)
            print(f"✅ Audio loaded from video: {len(audio)} samples")
            
            # ======================
            # STEP 2: Transcribe with Whisper
            # ======================
            progress(0.3, desc="🤖 Loading Whisper model...")
            print("2️⃣ Loading Whisper model...")
            model = whisperx.load_model(
                "large-v2",  # Options: tiny, base, small, medium, large-v2, large-v3
                self.device,
                compute_type=self.compute_type,
                language="en"
            )
            
            progress(0.4, desc="📝 Transcribing audio...")
            print("3️⃣ Transcribing audio...")
            result = model.transcribe(audio, batch_size=self.batch_size)
            print(f"✅ Transcription complete ({result['language']} detected)")
            
            # ======================
            # STEP 3: Align Timestamps
            # ======================
            progress(0.5, desc="⏱️ Aligning timestamps...")
            print("4️⃣ Aligning word-level timestamps...")
            model_a, metadata = whisperx.load_align_model(
                language_code=result["language"],
                device=self.device
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False
            )
            print("✅ Timestamps aligned")
            
            # Clean up Whisper model to free memory
            progress(0.6, desc="🧹 Freeing memory...")
            del model
            gc.collect()
            
            # ======================
            # STEP 4: Speaker Diarization - CORRECT IMPORT
                                                        # STEP 4: Speaker Diarization - Official pyannote method
            # ======================
            progress(0.7, desc="👥 Loading diarization model...")
            print("5️⃣ Loading speaker diarization model...")
            
            diarize_model = DiarizationPipeline(
                model_name="pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
                device=self.device
            )
            
            # # Use official pyannote Pipeline
            # diarize_model = Pipeline.from_pretrained(
            #     "pyannote/speaker-diarization-community-1",
            #     use_auth_token=self.hf_token
            # )
            
            # Move to device
            if self.device == "cuda":
                diarize_model.to(torch.device("cuda"))
        

            progress(0.8, desc="🔊 Identifying speakers...")
            print("6️⃣ Performing speaker diarization...")
            diarize_segments = diarize_model(audio)
            print("✅ Speaker diarization complete")
            
            # ======================
            # STEP 5: Assign Speakers to Words
            # ======================
            progress(0.9, desc="🔗 Assigning speakers...")
            print("7️⃣ Assigning speakers to transcript...")
            result = whisperx.assign_word_speakers(diarize_segments, result)
            print("✅ Speaker assignment complete")
            
            progress(1.0, desc="✅ Complete!")
            
            # ======================
            # STEP 6: Format Results
            # ======================
            processing_time = time.time() - start_time
            transcription = self._format_results(result)
            timing_info = self._get_timing_info(result, processing_time, video_file)
            
            return transcription, timing_info
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(f"FULL ERROR: {error_msg}")
            
            # More specific error handling
            if "DiarizationPipeline" in str(e):
                error_msg += "\n\n💡 DiarizationPipeline import issue. Try:\n" \
                           "1. Update WhisperX: pip install --upgrade whisperx\n" \
                           "2. Check if from whisperx.diarize import DiarizationPipeline works"
            elif "authentication" in str(e).lower():
                error_msg += "\n\n💡 Authentication issue. Please:\n" \
                           "1. Check your Hugging Face token\n" \
                           "2. Accept model agreements"
            
            return error_msg, "Check console for details"
    
    def _format_results(self, result):
        """Format the final results"""
        if not result["segments"]:
            return "No transcription segments found"
        
        output = "## 🎯 Video Transcription with Speaker Identification\n\n"
        
        current_speaker = None
        for segment in result["segments"]:
            speaker = segment.get("speaker", "UNKNOWN")
            start_time = self._format_timestamp(segment["start"])
            
            if speaker != current_speaker:
                output += f"\n**👤 {speaker}:**\n"
                current_speaker = speaker
            
            output += f"[{start_time}] {segment['text'].strip()}\n"
        
        # Add summary
        speakers = set(segment.get("speaker", "UNKNOWN") for segment in result["segments"])
        output += f"\n---\n**Speakers Detected:** {len(speakers)} | **Segments:** {len(result['segments'])}"
        
        return output
    
    def _get_timing_info(self, result, processing_time, video_file):
        """Generate timing information"""
        if not result["segments"]:
            return "No timing information available"
        
        total_duration = result["segments"][-1]["end"]
        speed_ratio = total_duration / processing_time if processing_time > 0 else 0
        
        video_name = os.path.basename(video_file) if video_file else "Unknown"
        
        return f"""
## ⏱️ Processing Statistics

**Video File:** {video_name}
\n**Audio Duration:** {self._format_timestamp(total_duration)}
**Processing Time:** {processing_time:.1f} seconds
**Speed Ratio:** {speed_ratio:.2f}x
\n**Status:** {"Faster than real-time" if speed_ratio > 1 else "Slower than real-time"}
**Device:** {self.device.upper()}
**Completed:** {datetime.now().strftime("%H:%M:%S")}
"""
    
    def _format_timestamp(self, seconds):
        """Convert seconds to MM:SS format"""
        if seconds is None:
            return "00:00"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

# Initialize system
fixed_diarization_system = FixedDiarizationV3()

# Gradio Interface
with gr.Blocks(title="Fixed Video Diarization") as demo:
    gr.Markdown("# 🎬 V3: Fixed Video Speaker Diarization")
    gr.Markdown("Upload your **Zoom** MP4 to identify who said what with speaker diarization")
    
    with gr.Row():
        with gr.Column():
            video_input = gr.Video(
                label="📹 Upload Zoom Video",
                sources=["upload", "webcam"],
                include_audio = True,
            )
            
            transcribe_btn = gr.Button("🎬 Transcribe with Speakers", variant="primary")
            
            gr.Markdown("""
            **Fixed Issues:**
            - ✅ Correct DiarizationPipeline import
            - ✅ Direct video processing
            - ✅ Memory management
            - ✅ Progress tracking
            """)
        
        with gr.Column():
            output_text = gr.Textbox(
                label="📄 Speaker Transcription",
                lines=18,
                value="Transcription with speaker identification will appear here..."
            )
            
            timing_info = gr.Markdown(
                label="⏱️ Processing Info"
            )
    
    transcribe_btn.click(
        fn=fixed_diarization_system.transcribe_video_with_speakers,
        inputs=video_input,
        outputs=[output_text, timing_info]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)