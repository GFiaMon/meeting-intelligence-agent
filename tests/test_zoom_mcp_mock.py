import sys
import os
# Add project root to path to allow running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.zoom_mcp.processor import ZoomProcessor
from src.zoom_mcp.normalizer import TranscriptNormalizer

@pytest.mark.asyncio
async def test_zoom_processor_flow():
    # 1. Setup Mocks
    processor = ZoomProcessor()
    
    # Mock PineconeManager to avoid real API calls
    processor.pinecone_mgr = MagicMock()
    processor.pinecone_mgr.upsert_documents = MagicMock()
    
    # 2. Simulate Zoom Messages
    # We send 6 messages to trigger the batch flush (batch_size=5)
    messages = [
        {"meeting_id": "test_123", "speaker_name": "Alice", "text": "Hello world 1", "timestamp": 1000},
        {"meeting_id": "test_123", "speaker_name": "Bob", "text": "Hello world 2", "timestamp": 2000},
        {"meeting_id": "test_123", "speaker_name": "Alice", "text": "Hello world 3", "timestamp": 3000},
        {"meeting_id": "test_123", "speaker_name": "Bob", "text": "Hello world 4", "timestamp": 4000},
        {"meeting_id": "test_123", "speaker_name": "Alice", "text": "Hello world 5", "timestamp": 5000},
        {"meeting_id": "test_123", "speaker_name": "Bob", "text": "Hello world 6", "timestamp": 6000},
    ]
    
    print("\n🧪 Sending 6 mock messages to processor...")
    for msg in messages:
        await processor.process_message(msg)
        
    # 3. Verify Batch Flush
    # Batch size is 5, so after 6 messages, upsert should have been called once
    # and 1 message should remain in the new batch
    
    # Wait a bit for the async thread to complete (since upsert is run in a thread)
    await asyncio.sleep(0.1)
    
    assert processor.pinecone_mgr.upsert_documents.called
    call_args = processor.pinecone_mgr.upsert_documents.call_args
    upserted_docs = call_args[0][0]
    
    print(f"✅ Upsert called with {len(upserted_docs)} documents")
    assert len(upserted_docs) == 5
    assert upserted_docs[0].page_content.endswith("Hello world 1")
    
    # 4. Verify Remaining Batch
    print(f"✅ Remaining in batch: {len(processor.batch)}")
    assert len(processor.batch) == 1
    assert processor.batch[0].page_content.endswith("Hello world 6")
    
    # 5. Close and Verify Final Flush
    await processor.close()
    await asyncio.sleep(0.1)
    
    # Should be called again for the last item
    assert processor.pinecone_mgr.upsert_documents.call_count == 2
    print("✅ Final flush successful")

if __name__ == "__main__":
    # Manual run wrapper
    asyncio.run(test_zoom_processor_flow())
