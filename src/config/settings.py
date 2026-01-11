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
    # Model Settings 1 (Default)
    # MODEL_NAME = "gpt-3.5-turbo"
    # METADATA_MODEL = "gpt-4o-mini" # Cheaper model for metadata extraction

    # Model Settings 2 (Upgrade Setup)
    # Primary Brain: Fixes routing bugs and reduces latency
    # Significantly better at tool-calling than 3.5 Turbo
    # MODEL_NAME = "gpt-4.1-mini"
    # Extraction: Swap to 5-nano for cost, or 5-mini for "better than ok" results
    # For Speaker Mapping, 5-nano is sufficient; 5-mini is the high-quality choice.
    # METADATA_MODEL = "gpt-5-mini"

    # Model Settings 3 (Power Setup)
    # THE BRAIN: GPT-5.2 (Reasoning Model)
    # Why: 98.7% tool-use accuracy. It "thinks" before it acts.
    # Cost: $1.75/1M input. This will solve your routing bugs.
    MODEL_NAME = "gpt-5.2" 
    # THE WORKER: GPT-5-mini
    # Why: High-speed extraction with reasoning capabilities. 
    # Better than 4o-mini at inferring speaker roles from context.
    METADATA_MODEL = "gpt-5-mini"


    # # Zoom API Settings
    # ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
    # ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
    # ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
    # ZOOM_WEBHOOK_SECRET = os.getenv("ZOOM_WEBHOOK_SECRET")

    # Pinecone Settings
    PINECONE_INDEX = "meeting-transcripts-1-dev"
    PINECONE_ENVIRONMENT = "us-west1-gcp"  # Change to your environment
    PINECONE_NAMESPACE = "development" # Default namespace for environment isolation options: "default", "development", "production"
    
    # LangSmith Settings (optional - for tracing and debugging)
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "meeting-agent")
    
    # Service Configuration
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
    
    # Model Settings
    WHISPER_MODEL = "small" # Options: tiny, base, small, medium, large-v2, large-v3
    
    # MCP (Model Context Protocol) Settings
    ENABLE_MCP = os.getenv("ENABLE_MCP", "false").lower() == "true"
    # Read from NOTION_TOKEN (the variable name in .env)
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
    
    # MCP Server Configurations
    @staticmethod
    def get_mcp_servers():
        """Get MCP server configurations."""
        if not Config.ENABLE_MCP:
            return {}

        servers = {}
        
        # 1. Notion MCP Server (if token is present)
        if Config.NOTION_TOKEN:
            servers["notion"] = {
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "transport": "stdio",
                "env": {
                    "NOTION_TOKEN": Config.NOTION_TOKEN
                }
            }
            
        # 2. World Time MCP Server (Remote HF Space)
        # This connects to your Space running app_world_time_mcp_server.py
        servers["world_time"] = {
            "url": "https://gfiamon-date-time-mpc-server-tool.hf.space/gradio_api/mcp/sse",
            "transport": "sse"
        }
        
        return servers


# Enable LangSmith tracing if configured
if Config.LANGCHAIN_TRACING_V2 == "true" and Config.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = Config.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = Config.LANGCHAIN_PROJECT
    print(f"✅ LangSmith tracing enabled for project: {Config.LANGCHAIN_PROJECT}")
