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
    speaker_data = [
        {"text": "Hello world.", "start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"text": "This is a test.", "start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"}
    ]
    docs = process_transcript_to_documents("full text ignored", speaker_data, "meeting-123")
    
    assert len(docs) == 2
    assert docs[0].page_content == "Hello world."
    assert docs[0].metadata["speaker"] == "SPEAKER_00"
    assert docs[0].metadata["meeting_id"] == "meeting-123"
    print(f"Processed {len(docs)} documents successfully.")

print("All tests passed!")
