import whisperx
import torch
import gc
import os

def transcribe_audio(audio_path: str, device="cuda", batch_size=16, compute_type="float16"):
    """
    Transcribes audio using WhisperX.
    Returns raw transcript output (list of segments with text, start, end).
    """
    print(f"1️⃣ Loading audio from {audio_path}...")
    audio = whisperx.load_audio(audio_path)
    
    print("2️⃣ Loading Whisper model...")
    model = whisperx.load_model(
        "large-v2", 
        device, 
        compute_type=compute_type, 
        language="en"
    )
    
    print("3️⃣ Transcribing audio...")
    result = model.transcribe(audio, batch_size=batch_size)
    
    print("4️⃣ Aligning word-level timestamps...")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], 
        device=device
    )
    result = whisperx.align(
        result["segments"], 
        model_a, 
        metadata, 
        audio, 
        device, 
        return_char_alignments=False
    )
    
    # Cleanup
    del model
    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    return result, audio # Return audio object for diarization
