# config.py
import os
from dotenv import load_dotenv
import torch

import warnings
warnings.filterwarnings("ignore", message="torchaudio._backend.list_audio_backends has been deprecated")
# warnings.filterwarnings("ignore", message="Model was trained with.*Bad things might happen")
warnings.filterwarnings("ignore", message="std(): degrees of freedom is <= 0")

load_dotenv()

class Config:
    # API Keys
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-3.5-turbo"

    # Pinecone Settings
    PINECONE_INDEX = "meeting-transcripts-1-dev"
    PINECONE_ENVIRONMENT = "us-west1-gcp"  # Change to your environment
    
    # Service Configuration
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
    
    # Model Settings
    WHISPER_MODEL = "small" # Options: tiny, base, small, medium, large-v2, large-v3
