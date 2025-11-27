# core/transcription_service.py
import whisperx
import gradio as gr
import gc
import time
import os
from datetime import datetime
from config import Config

# CORRECT WAY: Import DiarizationPipeline at point of use
from whisperx.diarize import DiarizationPipeline

class TranscriptionService:
    def __init__(self):
        self.config = Config
        self.models_loaded = False
        self.whisper_model = None
        self.diarize_model = None
        self.batch_size = 16

        
    def load_models(self):
        """Load AI models once - use pre-loaded models from init"""
        if not self.models_loaded:
            print("📥 Loading transcription models...")
            
            # Use the model from config instead of hardcoding
            self.whisper_model = whisperx.load_model(
                self.config.WHISPER_MODEL,
                self.config.DEVICE,
                compute_type=self.config.COMPUTE_TYPE,
                language="en"
            )
            
            self.diarize_model = DiarizationPipeline(
                use_auth_token=self.config.HUGGINGFACE_TOKEN,
                device=self.config.DEVICE
            )
            
            self.models_loaded = True
            print("✅ Models loaded successfully")


    def transcribe_video(self, video_file_path, progress_callback=None):
            """Clean transcription pipeline without Gradio dependencies.
            Added optional progress callback"""
            try:
                if not self.models_loaded:
                    self.load_models()
                
                start_time = time.time()
                print(f"🎬 Processing video: {os.path.basename(video_file_path)}")
                
                # ======================
                # STEP 1: Load Audio from Video
                # ======================
                if progress_callback:
                    progress_callback(0.1, "🎬 Loading audio from video...")
                print("1️⃣ Loading audio directly from video...")
                audio = whisperx.load_audio(video_file_path)

                print(f"✅ Audio loaded: {len(audio)} samples")
                
                # ======================
                # STEP 2: Transcribe with Whisper
                # ======================
                print("2️⃣ Loading Whisper model...")
                if progress_callback:
                    progress_callback(0.3, "🤖 Loading Whisper model...")

                if progress_callback:
                    progress_callback(0.4, "📝 Transcribing audio...")
                print("3️⃣ Transcribing audio...")

                result = self.whisper_model.transcribe(audio, batch_size=self.batch_size)
                print(f"✅ Transcription complete ({result['language']} detected)")            
                
                # ======================
                # STEP 3: Align Timestamps
                # ======================
                if progress_callback:
                    progress_callback(0.5, "⏱️ Aligning timestamps...")
                print("4️⃣ Aligning word-level timestamps...")
                
                model_a, metadata = whisperx.load_align_model(
                    language_code=result["language"],
                    device=self.config.DEVICE
                )
                result = whisperx.align(
                    result["segments"],
                    model_a,
                    metadata,
                    audio,
                    self.config.DEVICE,
                    return_char_alignments=False
                )
                print("✅ Timestamps aligned")
                
                # ======================
                # STEP 4: Speaker Diarization - CORRECT IMPORT
                # ======================
                if progress_callback:
                    progress_callback(0.7, "👥 Identifying speakers...")
                print("5️⃣ Loading speaker diarization model...")
                diarize_segments = self.diarize_model(audio)            
                    
                
                # ======================
                # STEP 5: Assign speakers
                # ======================
                #
                if progress_callback:
                    progress_callback(0.9, "🔗 Assigning speakers to text...")
                result = whisperx.assign_word_speakers(diarize_segments, result)
                print("6️⃣ Assigning speakers to transcript...")
                             
                print("🔗 Assigning speakers to text...")
                result = whisperx.assign_word_speakers(diarize_segments, result)
                print("✅ Speaker assignment complete")
                

                if progress_callback:
                    progress_callback(1.0, "✅ Complete!")
                    
                # ======================
                # STEP 6: Format results
                # ======================
                processing_time = time.time() - start_time
                transcription = self._format_results(result)
                timing_info = self._get_timing_info(result, processing_time, video_file_path)
                
                return {
                    "success": True,
                    "transcription": transcription,
                    "timing_info": timing_info,
                    "raw_data": result,  # Keep for potential storage
                    "processing_time": processing_time,
                    "speakers_count": len(set(seg.get("speaker", "UNKNOWN") for seg in result["segments"]))
                }
                
            except Exception as e:
                error_msg = f"Transcription failed: {str(e)}"
                print(f"❌ ERROR: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
    

    def _format_results(self, result):
        """Format transcription with speaker labels"""
        if not result["segments"]:
            return "No transcription segments found"
        
        output = "## 🎯 Transcription with Speaker Identification\n\n"
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
        output += f"\n---\n**Speakers:** {len(speakers)} | **Segments:** {len(result['segments'])}"
        
        return output
    
    def _get_timing_info(self, result, processing_time, video_file_path):
        """Generate timing information"""
        if not result["segments"]:
            return "No timing information available"
        
        total_duration = result["segments"][-1]["end"]
        speed_ratio = total_duration / processing_time if processing_time > 0 else 0
        video_name = os.path.basename(video_file_path)
        
        return f"""
## ⏱️ Processing Statistics

**File:** {video_name}
\n**Duration:** {self._format_timestamp(total_duration)}
**Processing Time:** {processing_time:.1f}s
\n**Speed:** {speed_ratio:.1f}x ({'Faster' if speed_ratio > 1 else 'Slower'} than real-time)
**Completed:** {datetime.now().strftime("%H:%M:%S")}
"""
    
    def _format_timestamp(self, seconds):
        """Convert seconds to MM:SS format"""
        if seconds is None:
            return "00:00"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"