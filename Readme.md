# Meeting Intelligence Agent

> Capstone Project: AI-powered meeting transcription and Q&A system

## 🎯 Project Vision
Build an intelligent agent that transcribes meetings, identifies speakers, and answers questions about past discussions.

## 🚀 Quick Start
```bash
# Local development
pip install -r requirements.txt
python app.py

# Or for Hugging Face Spaces deployment
# File automatically detected as app.py in root
```

## 📊 Current Progress

### ✅ COMPLETED (Research Phase - Archived)
- **V1**: Basic audio transcription with Whisper
- **V2**: Video processing with timestamps  
- **V3**: Speaker diarization with WhisperX + PyAnnote
- *Located in: `archive_research/`*

### 🚧 IN PROGRESS (Development Phase)
- **Main App**: `app.py` (unified Gradio interface)
- **RAG System**: Pinecone vector database
- **Agent Development**: LangChain meeting Q&A
- **Integration**: Transcription → Storage → Chat pipeline

## 🏗️ Technical Architecture

```
Video Input → WhisperX Transcription → Speaker Diarization → Meeting Summary & Format → 
Pinecone Storage → LangChain Agent → Gradio Chat Interface
                      ↖_______________↙
                          Q&A Loop
```

## 🛠️ Tech Stack
- **Main App**: `app.py` (Gradio root file for Hugging Face)
- **Transcription**: WhisperX, PyAnnote
- **Vector DB**: Pinecone
- **AI Framework**: LangChain, OpenAI
- **Frontend**: Gradio
- **Deployment**: Hugging Face Spaces

## 📁 Project Structure
```
meeting-agent-transcription-experiments/
├── app.py              # 🎯 Main application (Hugging Face compatible)
├── core/               # Backend logic modules
├── archive_research/   # 🗂️ Research experiments (V1-V3)
├── utils/              # Helper functions
├── requirements.txt    # Dependencies
└── README.md          # This file
```

## 🎯 Next Development Tasks
1. [ ] Build `core/pinecone_manager.py`
2. [ ] Create `core/rag_pipeline.py` 
3. [ ] Develop `core/meeting_agent.py`
4. [ ] Integrate everything into `app.py`
5. [ ] Test end-to-end workflow

## 🔧 Key Dependencies
```txt
gradio>=4.0.0
whisperx>=3.1.1
langchain>=0.1.0
pinecone-client>=3.0.0
openai>=1.0.0
python-dotenv>=1.0.0
```

## 📋 Deployment Notes
- **Hugging Face Spaces** looks for `app.py` in root
- **Environment variables** via Spaces secrets
- **Large models** are downloaded on first run
- **Asset files** should be in `assets/` folder

---

**You're absolutely right!** For Hugging Face Spaces deployment, the main file needs to be `app.py` in the root. Here's the corrected structure:

## 📁 Corrected Project Structure

```
meeting-agent-transcription-experiments/
├── app.py                          # 🎯 MAIN APP (for Hugging Face)
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── core/                           # Core backend modules
│   ├── __init__.py
│   ├── pinecone_manager.py
│   ├── rag_pipeline.py
│   ├── meeting_agent.py
│   └── agent_tools.py
├── archive_research/               # 🗂️ Research & experiments archive
│   ├── v1_audio_transcriber.py
│   ├── v2_video_transcriber.py
│   ├── v3_speaker_diarization.py
│   ├── v3_improved_diarization.py
│   └── basic_chatbot_tests/
├── utils/                          # Utilities
│   ├── __init__.py
│   ├── config.py
│   ├── embedding_utils.py
│   └── audio_utils.py
└── assets/                         # For deployment assets
    ├── sample_meeting.mp4
    └── demo_instructions.md
```
