
# Deployment Guide

> **Meeting Intelligence Agent - Deployment Documentation**

---

## 📋 Table of Contents

- [Local Development](#-local-development)
  - [Environment Setup](#1-environment-setup)
  - [API Keys Configuration](#2-api-keys-configuration)
  - [Initialize Pinecone](#3-initialize-pinecone-to-test-connection)
  - [Run Application](#4-run-application)
  - [Pinecone Management](#5-pinecone-management)
- [Docker Deployment](#-docker-deployment)
  - [Build Docker Image](#1-build-docker-image)
  - [Run Container](#2-run-container)
  - [Docker Compose](#3-docker-compose-recommended)
- [Hugging Face Spaces Deployment](#-hugging-face-spaces-deployment)
  - [Create New Space](#1-create-new-space)
  - [Configure Space Settings](#2-configure-space-settings)
  - [Upload Files](#3-upload-files)
  - [Configure Dockerfile](#4-configure-dockerfile)
  - [Build and Deploy](#5-build-and-deploy)
  - [Enable Auto-Redeploy](#6-enable-auto-redeploy)
- [Custom MCP Server Deployment](#-custom-mcp-server-deployment)
  - [World Time Server](#world-time-server)
  - [Update Main Agent Configuration](#update-main-agent-configuration)
- [Production Considerations](#-production-considerations)
  - [Security](#1-security)
  - [Performance Optimization](#2-performance-optimization)
  - [Monitoring](#3-monitoring)
  - [Scaling](#4-scaling)
  - [Database Maintenance](#5-database-maintenance)

---

## Local Development

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/yourusername/meeting-agent.git
cd meeting-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (required for audio processing)
# MacOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install ffmpeg

# Windows (PowerShell as Admin):
choco install ffmpeg
```

### 2. API Keys Configuration
Create `.env` file:
```bash
# Required
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=meetings
PINECONE_ENVIRONMENT=us-east-1

# Optional - for MCP features
ENABLE_MCP=true
NOTION_TOKEN=secret_...

# Optional - for LangSmith monitoring
LANGSMITH_API_KEY=ls_...
LANGSMITH_PROJECT=meeting-agent
LANGSMITH_TRACING=true

# Optional - for Zoom integration (future)
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ZOOM_WEBHOOK_SECRET=...
```

### 3. Initialize Pinecone (to test connection)
```bash
# Run setup script
python scripts/setup_pinecone.py

# Or manually:
python -c "
import pinecone
import os
from dotenv import load_dotenv

load_dotenv()

pinecone.init(
    api_key=os.getenv('PINECONE_API_KEY'),
    environment=os.getenv('PINECONE_ENVIRONMENT')
)

index_name = os.getenv('PINECONE_INDEX')
if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine'
    )
    print(f'Index {index_name} created')
else:
    print(f'Index {index_name} already exists')
"
```

### 4. Run Application
```bash
# Start the Gradio app
python app.py

# Access at: http://localhost:7860
```

### 5. Pinecone Management
Use the management script to verify and manage your database:
```bash
# Check if meetings are being stored
python scripts/manage_pinecone.py stats

# List existing meetings
python scripts/manage_pinecone.py list

# Example output:

Found 2 unique meeting(s):

--------------------------------------------------------------------------------
1. Meeting ID: doc_2659a111
   Title: Meeting 1: Agentic Chatbot Project Check-In 
   Date: 2025-10-12
   Duration: N/A
   Source File: notion_upload
   Participants: Mark, John, Jane
--------------------------------------------------------------------------------
2. Meeting ID: meeting_252aa222
   Title: Quarterly ML Project Review
   Date: 2025-12-02
   Duration: 03:39
   Source File: quarterly_ml_project_review.mp4
   Participants: Mark, John, Jane
--------------------------------------------------------------------------------

```

---

## Docker Deployment

### 1. Build Docker Image
```bash
# Build with standard dependencies
docker build -t meeting-agent .

# Or build for Hugging Face Spaces
cp requirements_hf.txt requirements.txt
docker build -t meeting-agent-hf .
```

### 2. Run Container
```bash
# Simple run
docker run -p 7860:7860 meeting-agent

# With environment variables
docker run -p 7860:7860 \
  -e OPENAI_API_KEY=sk-... \
  -e PINECONE_API_KEY=... \
  meeting-agent

# With .env file
docker run -p 7860:7860 \
  --env-file .env \
  meeting-agent

# With volume for persistent storage
docker run -p 7860:7860 \
  --env-file .env \
  -v meeting_data:/app/data \
  meeting-agent
```

### 3. Docker Compose (Recommended)
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  meeting-agent:
    build: .
    ports:
      - "7860:7860"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX=${PINECONE_INDEX}
      - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
      - ENABLE_MCP=${ENABLE_MCP:-false}
      - NOTION_TOKEN=${NOTION_TOKEN}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

---

## Hugging Face Spaces Deployment

### 1. Create New Space
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Select:
   - **Space name**: meeting-agent
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public or Private

### 2. Configure Space Settings
In your Space → Settings → Variables & Secrets:

**Add these secrets**:
```
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=meetings
PINECONE_ENVIRONMENT=us-east-1
```

**Optional**:
```
ENABLE_MCP=true
NOTION_TOKEN=secret_...
LANGSMITH_API_KEY=ls_...
```

### 3. Upload Files
Upload these files to your Space:
- `app.py`
- `requirements_hf.txt` (rename to `requirements.txt`)
- `Dockerfile`
- All files from `src/` directory
- `external_mcp_servers/` (if including custom servers)

### 4. Configure Dockerfile
Your `Dockerfile` should be optimized for HF Spaces:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements (use hf version)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK CMD curl --fail http://localhost:7860 || exit 1

# Run application
CMD ["python", "app.py"]
```

### 5. Build and Deploy
1. HF Spaces will automatically build when you push files
2. Monitor build logs in the Space "Logs" tab
3. Access your app at: `https://huggingface.co/spaces/username/meeting-agent`

### 6. Enable Auto-Redeploy
In Space Settings → Hardware:
- **CPU**: Basic (free) or upgrade for better performance
- **Sleep Time**: Set to prevent sleeping (upgraded spaces only)

---

## Custom MCP Server Deployment

### World Time Server
1. **Create new Space** for time server
2. **Select SDK**: Gradio
3. **Upload files** from `external_mcp_servers/time_mcp_server/`
4. **Set app file**: `app_file: app_world_time_mcp_server.py`
5. **Deploy**: Space will be available at `username-time-server.hf.space`

### Update Main Agent Configuration
In `src/config/settings.py`:
```python
# Update the URL to your deployed time server
servers["world_time"] = {
    "url": "https://username-time-server.hf.space/gradio_api/mcp/sse",
    "transport": "sse"
}
```

--- 

## Production Considerations

### 1. Security
```python
# app.py - Security headers
import gradio as gr

app = gr.Blocks()

# Add CORS and security headers
app.cors = True
app.headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
}
```

### 2. Performance Optimization
- **Enable caching** for embeddings
- **Improve Agent Architecture** to improve tool usage
- **Improve modularization** to improve code organization
- **Create Transcription MCP Server** to improve performance
- **Use batch processing** for multiple meetings
- **Implement rate limiting** for API calls
- **Monitor memory usage** for long videos

### 3. Monitoring
- **LangSmith**: For agent tracing and metrics
- **Prometheus/Grafana**: For system metrics
- **Logging**: Structured logging with JSON format

### 4. Scaling
- **Horizontal scaling**: Multiple agent instances
- **Database scaling**: Pinecone pod size adjustments
- **Load balancing**: Nginx/Traefik for multiple instances

### 5. Database Maintenance
Regularly monitor and maintain your Pinecone index:
```bash
# Weekly maintenance script
python scripts/manage_pinecone.py stats
# Check: Total meetings, chunks, namespace usage

# Cleanup old meetings (if implementing retention policy)
python scripts/manage_pinecone.py delete-old --days 90
```
