# core/transcription_service.py
import whisperx
import gradio as gr
import gc
import time
import os
from datetime import datetime
import warnings

# Suppress specific pyannote/pytorch warning about degrees of freedom
warnings.filterwarnings("ignore", message="std\(\): degrees of freedom is <= 0")

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
                    print(f"DEBUG: Calling progress callback 0.1. Type: {type(progress_callback)}")
                    try:
                        progress_callback(0.1, desc="🎬 Loading audio from video...")
                        print("DEBUG: Progress callback 0.1 called successfully")
                    except Exception as e:
                        print(f"DEBUG: Error calling progress callback: {e}")
                    time.sleep(0.5)
                print("1️⃣ Loading audio directly from video...")
                audio = whisperx.load_audio(video_file_path)

                print(f"✅ Audio loaded: {len(audio)} samples")
                
                # ======================
                # STEP 2: Transcribe with Whisper
                # ======================
                print("2️⃣ Loading Whisper model...")
                if progress_callback:
                    progress_callback(0.3, desc="🤖 Loading Whisper model...")
                    time.sleep(0.5)

                if progress_callback:
                    progress_callback(0.4, desc="📝 Transcribing audio...")
                    time.sleep(0.5)
                print("3️⃣ Transcribing audio...")

                result = self.whisper_model.transcribe(audio, batch_size=self.batch_size)
                detected_language = result['language']  # Save language before it gets lost
                print(f"✅ Transcription complete ({detected_language} detected)")            
                
                # ======================
                # STEP 3: Align Timestamps
                # ======================
                if progress_callback:
                    progress_callback(0.5, desc="⏱️ Aligning timestamps...")
                    time.sleep(0.5)
                print("4️⃣ Aligning word-level timestamps...")
                
                # Load the alignment model and its metadata from whisperx for word-level timestamp alignment.
                model_a, metadata = whisperx.load_align_model(
                    language_code=detected_language,
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
                # Restore language to result dict after alignment
                result["language"] = detected_language
                print("✅ Timestamps aligned")
                
                # ======================
                # STEP 4: Speaker Diarization - CORRECT IMPORT
                # ======================
                if progress_callback:
                    progress_callback(0.7, desc="👥 Identifying speakers...")
                    time.sleep(0.5)
                print("5️⃣ Loading speaker diarization model...")
                diarize_segments = self.diarize_model(audio)            
                    
                
                # ======================
                # STEP 5: Assign speakers
                # ======================
                #
                if progress_callback:
                    progress_callback(0.9, desc="🔗 Assigning speakers to text...")
                    time.sleep(0.5)
                result = whisperx.assign_word_speakers(diarize_segments, result)
                print("6️⃣ Assigning speakers to transcript...")
                             
                print("🔗 Assigning speakers to text...")
                result = whisperx.assign_word_speakers(diarize_segments, result)
                print("✅ Speaker assignment complete")
                

                if progress_callback:
                    progress_callback(1.0, desc="✅ Complete!")
                    time.sleep(0.5)
                    
                # ======================
                # STEP 6: Format results
                # ======================
                processing_time = time.time() - start_time
                transcription = self._format_results(result, video_file_path)
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
    

    def _format_results(self, result, video_file_path):
        """Format transcription with speaker labels and comprehensive meeting metadata"""
        if not result["segments"]:
            return "No transcription segments found"
        
        # Extract meeting metadata
        segments = result["segments"]
        speakers = set(segment.get("speaker", "UNKNOWN") for segment in segments)
        total_duration = segments[-1]["end"] if segments else 0
        language = result.get("language", "unknown")
        
        # Calculate statistics
        total_words = sum(len(seg.get("text", "").split()) for seg in segments)
        avg_segment_length = total_words / len(segments) if segments else 0
        
        # Build header with meeting context
        output = "# 🎯 Meeting Transcription\n\n"
        output += "## 📋 Meeting Information\n\n"
        output += f"**📁 File:** `{os.path.basename(video_file_path)}`\n"
        output += f"**📅 Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        output += f"**⏱️ Duration:** {self._format_timestamp(total_duration)}\n"
        output += f"**👥 Speakers:** {len(speakers)}\n"
        output += f"**🌐 Language:** {language.upper()}\n"
        output += f"**🤖 Model:** {self.config.WHISPER_MODEL}\n\n"
        output += "---\n\n"
        output += "## 💬 Transcript\n\n"
        
        # Add transcript content
        current_speaker = None
        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            start_time = self._format_timestamp(segment["start"])
            
            if speaker != current_speaker:
                output += f"\n**👤 {speaker}:**\n"
                current_speaker = speaker
            
            output += f"[{start_time}] {segment['text'].strip()}\n"
        
        # Add comprehensive footer
        output += "\n---\n\n"
        output += "## 📊 Transcript Statistics\n\n"
        output += f"**Total Segments:** {len(segments)}\n"
        output += f"**Total Words:** {total_words:,}\n"
        output += f"**Avg Words/Segment:** {avg_segment_length:.1f}\n"
        output += f"**Unique Speakers:** {len(speakers)}\n"
        output += f"**Speaker IDs:** {', '.join(sorted(speakers))}\n"
        
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