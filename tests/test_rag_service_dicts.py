"""
Verification script for RagAgentService with dictionary history (Gradio default).
"""
import sys
import os
from unittest.mock import MagicMock, patch
from gradio import ChatMessage

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_agent_service import RagAgentService

def test_rag_service_dicts():
    print("🧪 Testing RagAgentService with Dictionary History...")
    
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
        
        # Test Generator Flow with DICTIONARY history
        print("\n1. Testing Generator Flow with Dicts:")
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"}
        ]
        
        gen = service.generate_response("How are you?", history)
        
        steps = list(gen)
        last_step = steps[-1]
        
        print(f"Total steps yielded: {len(steps)}")
        print(f"Final message list length: {len(last_step)}")
        
        # Verify structure
        # Expected: History (2) + New User Msg (1) + Thought (1) + Final Answer (1) = 5 messages
        assert len(last_step) == 5
        
        # Verify History Conversion
        msg0 = last_step[0]
        print(f"Msg 0 type: {type(msg0)}")
        assert isinstance(msg0, ChatMessage)
        assert msg0.content == "Hi"
        
        # Verify Thought Message
        thought_msg = last_step[-2]
        print(f"Thought Message: {thought_msg.content}")
        assert thought_msg.role == "assistant"
        assert "Thinking Process" in thought_msg.metadata["title"]
        
        print("✅ Generator flow with Dictionary history verified!")

if __name__ == "__main__":
    test_rag_service_dicts()
