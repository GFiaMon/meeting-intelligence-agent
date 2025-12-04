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
    METADATA_MODEL = "gpt-4o-mini" # Cheaper model for metadata extraction

    # Zoom API Settings
    ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
    ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
    ZOOM_WEBHOOK_SECRET = os.getenv("ZOOM_WEBHOOK_SECRET")

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
            
        # 2. Berlin Time MCP Server (SSE Mode)
        # Requires the server to be running separately: python external_mcp_servers/app_time_mcp_server.py
        servers["berlin_time"] = {
            "url": "https://gfiamon-date-time-mpc-server-tool.hf.space/gradio_api/mcp/",
            "transport": "sse"
        }
        
        return servers


# Enable LangSmith tracing if configured
if Config.LANGCHAIN_TRACING_V2 == "true" and Config.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = Config.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = Config.LANGCHAIN_PROJECT
    print(f"✅ LangSmith tracing enabled for project: {Config.LANGCHAIN_PROJECT}")
