"""
Test script for RagAgentService.
Verifies generator behavior, dynamic retrieval, and history parsing.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_agent_service import RagAgentService

def test_rag_service():
    print("🧪 Testing RagAgentService...")
    
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
        
        # Test 1: Generator yields thinking steps
        print("\n1. Testing Generator Flow:")
        gen = service.generate_response("Hello", [])
        
        steps = list(gen)
        print(f"Yielded steps: {steps}")
        
        assert "🔍 Analyzing your query..." in steps
        assert "📚 Searching meeting transcripts (fetching top 5 segments)..." in steps
        assert "Hello" in steps
        assert " world" in steps
        print("✅ Generator flow verified!")

        # Test 2: Dynamic Retrieval Logic
        print("\n2. Testing Dynamic Retrieval:")
        
        # Case A: Specific question
        kwargs_a = service._get_retrieval_kwargs("Who is the speaker?")
        print(f"Query: 'Who is the speaker?' -> kwargs: {kwargs_a}")
        assert kwargs_a["k"] == 5
        
        # Case B: Summary
        kwargs_b = service._get_retrieval_kwargs("Summarize the entire meeting")
        print(f"Query: 'Summarize the entire meeting' -> kwargs: {kwargs_b}")
        assert kwargs_b["k"] == 20
        
        # Case C: Meeting specific
        kwargs_c = service._get_retrieval_kwargs("Summarize meeting_12345678")
        print(f"Query: 'Summarize meeting_12345678' -> kwargs: {kwargs_c}")
        assert kwargs_c["k"] == 100
        assert kwargs_c["filter"]["meeting_id"]["$eq"] == "meeting_12345678"
        print("✅ Dynamic retrieval logic verified!")
        
        # Test 3: History Parsing
        print("\n3. Testing History Parsing:")
        history = [
            ["User says hi", "Bot says hello"],
            {"role": "user", "content": "Follow up"},
            "Garbage"
        ]
        parsed = service._parse_history(history)
        print(f"Parsed messages: {parsed}")
        assert len(parsed) == 3 # 2 from list + 1 from dict
        assert parsed[0].content == "User says hi"
        assert parsed[1].content == "Bot says hello"
        assert parsed[2].content == "Follow up"
        print("✅ History parsing verified!")

if __name__ == "__main__":
    test_rag_service()
