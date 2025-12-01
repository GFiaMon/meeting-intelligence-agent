
import os
import sys
from unittest.mock import MagicMock, patch

# Mock config to avoid loading .env
sys.modules["config"] = MagicMock()
from config import Config
Config.ENABLE_MCP = False
Config.MODEL_NAME = "gpt-3.5-turbo"
Config.OPENAI_API_KEY = "fake-key"

# Mock langchain components
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

# Mock PineconeManager
class MockPineconeManager:
    def get_retriever(self, namespace, search_kwargs):
        mock_retriever = MagicMock()
        # Mock invoke to return some dummy documents
        mock_retriever.invoke.return_value = [
            Document(page_content="Meeting content...", metadata={"meeting_id": "meeting_abc123", "date": "2023-10-27"})
        ]
        return mock_retriever

# Mock TranscriptionService
class MockTranscriptionService:
    pass

# Import the agent (we need to patch imports that might fail)
with patch.dict(sys.modules, {"core.pinecone_manager": MagicMock(), "core.transcription_service": MagicMock()}):
    from core.conversational_agent import ConversationalMeetingAgent
    from core.tools import initialize_tools

def run_test():
    # Initialize mocks
    pinecone_mgr = MockPineconeManager()
    transcription_svc = MockTranscriptionService()
    
    # Initialize agent
    agent = ConversationalMeetingAgent(pinecone_mgr, transcription_svc)
    
    # Mock the LLM to simulate the issue or at least see what it tries to do
    # We can't easily mock the LLM's decision making without an API key, 
    # but we can inspect the tools and the graph.
    
    print("Agent initialized.")
    
    # We can't fully run the agent without a real LLM or a sophisticated mock that simulates tool calls.
    # However, we can check the tools implementation directly with the input we suspect is causing issues.
    
    from core.tools import search_meetings
    
    print("\nTesting search_meetings with 'meeting 2'...")
    result = search_meetings.invoke({"query": "minutes", "meeting_id": "meeting 2"})
    print(f"Result: {result}")

if __name__ == "__main__":
    run_test()
