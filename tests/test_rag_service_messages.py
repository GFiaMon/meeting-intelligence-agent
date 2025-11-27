"""
Verification script for RagAgentService with ChatMessage objects.
"""
import sys
import os
from unittest.mock import MagicMock, patch
from gradio import ChatMessage

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_agent_service import RagAgentService

def test_rag_service_messages():
    print("🧪 Testing RagAgentService with ChatMessage objects...")
    
    # Mock PineconeManager
    mock_pinecone = MagicMock()
    mock_retriever = MagicMock()
    mock_pinecone.get_retriever.return_value = mock_retriever
    
    # Mock LLM streaming
    with patch("core.rag_agent_service.ChatOpenAI") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        # Mock stream method to yield chunks
        mock_llm_instance.stream.return_value = iter([
            MagicMock(content="Hello"), 
            MagicMock(content=" world")
        ])
        
        service = RagAgentService(mock_pinecone)
        
        # Test Generator Flow
        print("\n1. Testing Generator Flow:")
        history = [
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello")
        ]
        
        gen = service.generate_response("How are you?", history)
        
        steps = list(gen)
        last_step = steps[-1]
        
        print(f"Total steps yielded: {len(steps)}")
        print(f"Final message list length: {len(last_step)}")
        
        # Verify structure
        # Expected: History (2) + New User Msg (1) + Thought (1) + Final Answer (1) = 5 messages
        assert len(last_step) == 5
        
        # Verify Thought Message
        thought_msg = last_step[-2]
        print(f"Thought Message: {thought_msg.content}")
        print(f"Thought Metadata: {thought_msg.metadata}")
        assert thought_msg.role == "assistant"
        assert "Thinking Process" in thought_msg.metadata["title"]
        assert thought_msg.metadata["status"] == "done"
        
        # Verify Final Answer
        final_msg = last_step[-1]
        print(f"Final Answer: {final_msg.content}")
        assert final_msg.content == "Hello world"
        
        print("✅ Generator flow with ChatMessages verified!")

if __name__ == "__main__":
    test_rag_service_messages()
