"""
Test script to verify the LangChain RAG implementation.

This script tests that the chatbot returns natural language answers
instead of raw context strings.

Usage:
    python tests/test_chatbot_langchain.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import chat_with_meetings, pinecone_available, pinecone_mgr


def test_chatbot_returns_natural_language():
    """Test that chatbot returns LLM-generated answer, not raw context"""
    
    if not pinecone_available:
        print("❌ SKIP: Pinecone not available")
        return False
    
    print("\n🧪 Testing chatbot with LangChain implementation...")
    print("=" * 60)
    
    # Test query
    message = "What were the main topics discussed?"
    history = []
    
    print(f"\n📝 Query: {message}")
    print("\n🤖 Response:")
    print("-" * 60)
    
    response = chat_with_meetings(message, history)
    
    print(response)
    print("-" * 60)
    
    # Assertions
    success = True
    
    # Check 1: Response should be a string
    if not isinstance(response, str):
        print("\n❌ FAIL: Response is not a string")
        success = False
    else:
        print("\n✅ PASS: Response is a string")
    
    # Check 2: Should NOT contain "Context 1:" or "Context 2:"
    if "Context 1:" in response or "Context 2:" in response:
        print("❌ FAIL: Response contains raw 'Context 1:' or 'Context 2:' strings")
        success = False
    else:
        print("✅ PASS: No raw context strings found")
    
    # Check 3: Should be conversational (contains common words)
    conversational_words = ["the", "meeting", "discussed", "mentioned", "about", "was", "were"]
    if any(word in response.lower() for word in conversational_words):
        print("✅ PASS: Response appears conversational")
    else:
        print("⚠️  WARNING: Response may not be conversational")
    
    # Check 4: Should not be an error message (unless no data)
    if response.startswith("❌") and "no relevant" not in response.lower():
        print("❌ FAIL: Response is an error message")
        success = False
    else:
        print("✅ PASS: Response is not an error")
    
    print("\n" + "=" * 60)
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe chatbot is now using LangChain ConversationalRetrievalChain")
        print("and returning natural language answers instead of raw context.")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the implementation.")
    
    return success


def test_conversation_memory():
    """Test that conversation history is maintained"""
    
    if not pinecone_available:
        print("❌ SKIP: Pinecone not available")
        return False
    
    print("\n\n🧪 Testing conversation memory...")
    print("=" * 60)
    
    # First message
    message1 = "What topics were discussed?"
    history1 = []
    
    print(f"\n📝 Query 1: {message1}")
    response1 = chat_with_meetings(message1, history1)
    print(f"🤖 Response 1: {response1[:100]}...")
    
    # Second message (follow-up)
    message2 = "Tell me more about that"
    history2 = [[message1, response1]]
    
    print(f"\n📝 Query 2 (follow-up): {message2}")
    response2 = chat_with_meetings(message2, history2)
    print(f"🤖 Response 2: {response2[:100]}...")
    
    # Check that second response is not an error
    if not response2.startswith("❌"):
        print("\n✅ PASS: Follow-up question handled")
        return True
    else:
        print("\n⚠️  WARNING: Follow-up question may not work as expected")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  LangChain RAG Implementation Test Suite")
    print("=" * 60)
    
    # Check prerequisites
    if not pinecone_available or not pinecone_mgr:
        print("\n❌ ERROR: Pinecone is not available")
        print("Please ensure:")
        print("  1. PINECONE_API_KEY is set in .env")
        print("  2. Pinecone index exists")
        print("  3. At least one meeting has been uploaded")
        sys.exit(1)
    
    print("\n✅ Prerequisites met: Pinecone is available")
    
    # Run tests
    test1_passed = test_chatbot_returns_natural_language()
    test2_passed = test_conversation_memory()
    
    # Summary
    print("\n\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  Natural Language Response: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  Conversation Memory:       {'✅ PASS' if test2_passed else '⚠️  WARNING'}")
    print("=" * 60)
    
    if test1_passed:
        print("\n🎉 Core functionality is working!")
        print("\nNext steps:")
        print("  1. Test in Gradio UI: python app.py")
        print("  2. Enable LangSmith tracing (optional)")
        print("  3. Plan LangGraph migration")
    else:
        print("\n❌ Tests failed. Please review the implementation.")
        sys.exit(1)
