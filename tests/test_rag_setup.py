import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external modules BEFORE they are imported by our code
mock_pinecone = MagicMock()
sys.modules["pinecone"] = mock_pinecone
sys.modules["langchain_pinecone"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()

# Mock langchain modules
sys.modules["langchain"] = MagicMock()
sys.modules["langchain.text_splitter"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.documents"] = MagicMock()

# Mock specific classes
mock_pinecone.Pinecone = MagicMock()
sys.modules["langchain_pinecone"].PineconeVectorStore = MagicMock()
sys.modules["langchain_openai"].OpenAIEmbeddings = MagicMock()

# Setup RecursiveCharacterTextSplitter mock to behave somewhat realistically
class MockTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=100):
        pass
    def split_documents(self, docs):
        return docs # Pass through for testing
    def create_documents(self, texts, metadatas):
        # Return dummy documents
        from langchain_core.documents import Document
        return [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]

sys.modules["langchain.text_splitter"].RecursiveCharacterTextSplitter = MockTextSplitter

# Setup Document mock
class MockDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}

sys.modules["langchain_core.documents"].Document = MockDocument

# Mock environment variables
with patch.dict(os.environ, {"PINECONE_API_KEY": "mock-key", "OPENAI_API_KEY": "mock-key"}):
    
    print("Testing imports...")
    # Now we can import our modules
    from core.pinecone_manager import PineconeManager
    from core.rag_pipeline import process_transcript_to_documents
    from utils.embedding_utils import get_embedding_model
    print("Imports successful.")

    print("Testing PineconeManager initialization...")
    pm = PineconeManager(index_name="test-index")
    print("PineconeManager initialized.")

    print("Testing get_embedding_model...")
    emb = get_embedding_model()
    print("Embedding model initialized.")

    print("Testing process_transcript_to_documents...")
    
    # Create realistic test data with longer segments that will produce multiple 1500+ char chunks
    speaker_data = [
        # SPEAKER_00 - Will be grouped into first chunk (should reach ~1500+ chars)
        {"text": "Hello everyone, welcome to today's quarterly planning meeting. I'm excited to have you all here as we discuss our strategic initiatives for Q4.", "start": 0.0, "end": 8.0, "speaker": "SPEAKER_00"},
        {"text": "We have several critical topics on the agenda today that will shape our direction for the next three months and set us up for success in the new year.", "start": 8.0, "end": 16.0, "speaker": "SPEAKER_00"},
        {"text": "First and foremost, let's talk about our Q4 roadmap and the key strategic initiatives we need to prioritize across all departments.", "start": 16.0, "end": 24.0, "speaker": "SPEAKER_00"},
        {"text": "We need to align on our priorities, resource allocation, and ensure everyone understands their role in achieving our quarterly objectives.", "start": 24.0, "end": 32.0, "speaker": "SPEAKER_00"},
        {"text": "This includes our marketing campaigns, product development milestones, customer success initiatives, and sales targets for the quarter.", "start": 32.0, "end": 40.0, "speaker": "SPEAKER_00"},
        {"text": "We also need to carefully review our budget constraints and make sure we're staying on track with our financial goals while investing in the right areas.", "start": 40.0, "end": 48.0, "speaker": "SPEAKER_00"},
        {"text": "I want to emphasize the importance of cross-functional collaboration as we move forward. Each team's success depends on effective communication and coordination.", "start": 48.0, "end": 56.0, "speaker": "SPEAKER_00"},
        {"text": "Let me know if you have any questions about the agenda before we dive into the details. I want to make sure everyone is on the same page.", "start": 56.0, "end": 64.0, "speaker": "SPEAKER_00"},
        {"text": "We'll be covering marketing strategy, product roadmap, customer retention programs, and our hiring plans for the next quarter.", "start": 64.0, "end": 72.0, "speaker": "SPEAKER_00"},
        {"text": "I've also prepared some data and metrics that will help us make informed decisions about where to focus our efforts and resources.", "start": 72.0, "end": 80.0, "speaker": "SPEAKER_00"},
        
        # SPEAKER_01 - Will be grouped into second chunk (should reach ~1500+ chars)
        {"text": "Thanks so much for the comprehensive overview and for organizing this meeting. I really appreciate the level of detail you've provided.", "start": 80.5, "end": 88.0, "speaker": "SPEAKER_01"},
        {"text": "I have several questions about the marketing budget and how we're planning to allocate resources across different channels and campaigns.", "start": 88.0, "end": 96.0, "speaker": "SPEAKER_01"},
        {"text": "Specifically, I'm wondering about our digital advertising strategy and how we're planning to distribute funds between paid search, social media, and display advertising.", "start": 96.0, "end": 104.0, "speaker": "SPEAKER_01"},
        {"text": "Are we planning to increase our digital advertising spend this quarter compared to last quarter, or are we maintaining the same budget levels?", "start": 104.0, "end": 112.0, "speaker": "SPEAKER_01"},
        {"text": "And what about our content marketing initiatives? I'm curious about our blog strategy, video content production, and how we're planning to leverage SEO.", "start": 112.0, "end": 120.0, "speaker": "SPEAKER_01"},
        {"text": "I think we should also consider influencer partnerships and community building efforts as part of our overall marketing strategy for the quarter.", "start": 120.0, "end": 128.0, "speaker": "SPEAKER_01"},
        {"text": "Additionally, I'd like to understand how we're measuring ROI on our marketing investments and what KPIs we'll be tracking to evaluate success.", "start": 128.0, "end": 136.0, "speaker": "SPEAKER_01"},
        {"text": "It's important that we have clear metrics and accountability frameworks in place so we can optimize our spending and demonstrate value to stakeholders.", "start": 136.0, "end": 144.0, "speaker": "SPEAKER_01"},
        {"text": "I'm also interested in hearing about our customer acquisition cost targets and how we plan to improve our conversion rates across different channels.", "start": 144.0, "end": 152.0, "speaker": "SPEAKER_01"},
        {"text": "Finally, I'd love to discuss our email marketing strategy and how we're planning to segment our audience for more personalized and effective campaigns.", "start": 152.0, "end": 160.0, "speaker": "SPEAKER_01"},
    ]
    
    # Test with default parameters (min_chunk_size=1500, max_chunk_size=3000)
    docs = process_transcript_to_documents(
        "full text ignored", 
        speaker_data, 
        "meeting-123",
        meeting_metadata={"meeting_date": "2025-11-27", "source_file": "test.mp4"}
    )
    
    print(f"Created {len(docs)} chunks from {len(speaker_data)} segments")
    
    # Validate we got multiple chunks (should be 2 based on speaker grouping with 1500+ chars each)
    assert len(docs) >= 2, f"Expected at least 2 chunks, got {len(docs)}"
    
    # Validate first chunk
    first_chunk = docs[0]
    print(f"\nFirst chunk:")
    print(f"  Speaker: {first_chunk.metadata['speaker']}")
    print(f"  Char count: {first_chunk.metadata['char_count']}")
    print(f"  Word count: {first_chunk.metadata['word_count']}")
    print(f"  Time range: {first_chunk.metadata['start_time_formatted']} - {first_chunk.metadata['end_time_formatted']}")
    print(f"  Preview: {first_chunk.page_content[:100]}...")
    
    # Validate metadata structure
    assert "meeting_id" in first_chunk.metadata
    assert "meeting_date" in first_chunk.metadata
    assert "speaker" in first_chunk.metadata
    assert "speakers" in first_chunk.metadata
    assert "start_time" in first_chunk.metadata
    assert "end_time" in first_chunk.metadata
    assert "duration" in first_chunk.metadata
    assert "chunk_type" in first_chunk.metadata
    assert "chunk_index" in first_chunk.metadata
    assert "total_chunks" in first_chunk.metadata
    assert "word_count" in first_chunk.metadata
    assert "char_count" in first_chunk.metadata
    
    # Validate chunk sizes meet minimum requirement (1500 chars)
    for i, doc in enumerate(docs):
        char_count = doc.metadata['char_count']
        print(f"Chunk {i}: {char_count} chars, speaker: {doc.metadata['speaker']}")
        # Most chunks should be >= 1500, but last chunk might be smaller
        if i < len(docs) - 1:
            assert char_count >= 1500, f"Chunk {i} is below minimum: {char_count} chars (expected >= 1500)"
        else:
            # Last chunk can be smaller
            assert char_count > 100, f"Chunk {i} is too small: {char_count} chars"
    
    # Validate meeting metadata was passed through
    assert first_chunk.metadata["meeting_id"] == "meeting-123"
    assert first_chunk.metadata["meeting_date"] == "2025-11-27"
    assert first_chunk.metadata["source_file"] == "test.mp4"
    
    print(f"\n✅ Processed {len(docs)} documents successfully with semantic grouping!")
    print(f"   Average chunk size: {sum(d.metadata['char_count'] for d in docs) // len(docs)} chars")
    print(f"   All chunks meet minimum size requirement (1500+ chars)")

print("\n🎉 All tests passed!")
