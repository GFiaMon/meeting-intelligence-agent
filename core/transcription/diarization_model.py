import whisperx
from whisperx.diarize import DiarizationPipeline
import torch
import os

def add_speaker_labels(audio, transcript_result, hf_token, device="cuda"):
    """
    Performs speaker diarization and assigns speakers to the transcript.
    """
    print("5️⃣ Loading speaker diarization model...")
    diarize_model = DiarizationPipeline(
        model_name="pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
        device=device
    )
    
    print("6️⃣ Performing speaker diarization...")
    diarize_segments = diarize_model(audio)
    
    print("7️⃣ Assigning speakers to transcript...")
    result = whisperx.assign_word_speakers(diarize_segments, transcript_result)
    
    return result["segments"]
