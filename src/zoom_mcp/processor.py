import asyncio
from typing import List, Dict, Any
from src.retrievers.pinecone import PineconeManager
from src.zoom_mcp.normalizer import TranscriptNormalizer

class ZoomProcessor:
    """
    Processes incoming Zoom RTMS messages, normalizes them,
    and upserts them to Pinecone.
    """
    
    def __init__(self):
        self.pinecone_mgr = PineconeManager()
        self.normalizer = TranscriptNormalizer()
        self.batch: List[Dict[str, Any]] = []
        self.batch_size = 5 # Upsert every 5 chunks to reduce API calls
        self.lock = asyncio.Lock()

    async def process_message(self, message: Dict[str, Any]):
        """
        Callback for handling a raw message from ZoomClient.
        """
        # We only care about transcript messages
        # Note: Real Zoom messages have a specific structure, we assume 'text' field exists
        if "text" not in message:
            return

        meeting_id = message.get("meeting_id", "unknown_meeting")
        
        # Normalize
        doc = self.normalizer.normalize_zoom_chunk(message, meeting_id)
        
        if doc:
            async with self.lock:
                self.batch.append(doc)
                print(f"📥 Received chunk: {doc.page_content}")
                
                if len(self.batch) >= self.batch_size:
                    await self._flush_batch()

    async def _flush_batch(self):
        """
        Upserts the current batch to Pinecone.
        """
        if not self.batch:
            return
            
        try:
            print(f"🚀 Upserting {len(self.batch)} chunks to Pinecone...")
            # PineconeManager.upsert_documents is synchronous, so we run it in a thread
            # to avoid blocking the WebSocket loop
            await asyncio.to_thread(
                self.pinecone_mgr.upsert_documents,
                self.batch,
                namespace="default"
            )
            self.batch = []
        except Exception as e:
            print(f"❌ Error flushing batch: {e}")
            # Keep batch to retry? Or drop? For now, we drop to avoid memory leak
            self.batch = []

    async def close(self):
        """
        Flush remaining items.
        """
        async with self.lock:
            await self._flush_batch()
