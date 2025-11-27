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
    
    # LangSmith Settings (optional - for tracing and debugging)
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "meeting-agent")
    
    # Service Configuration
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
    
    # Model Settings
    WHISPER_MODEL = "small" # Options: tiny, base, small, medium, large-v2, large-v3

# Enable LangSmith tracing if configured
if Config.LANGCHAIN_TRACING_V2 == "true" and Config.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = Config.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = Config.LANGCHAIN_PROJECT
    print(f"✅ LangSmith tracing enabled for project: {Config.LANGCHAIN_PROJECT}")
