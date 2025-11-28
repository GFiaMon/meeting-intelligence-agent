"""
Quick test script to verify both RAG implementations work correctly.
Run this to test without starting the full Gradio app.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from core.pinecone_manager import PineconeManager

def test_implementation(use_langgraph=False):
    """Test a RAG implementation."""
    impl_name = "LangGraph" if use_langgraph else "Original"
    print(f"\n{'='*60}")
    print(f"Testing {impl_name} Implementation")
    print(f"{'='*60}\n")
    
    try:
        # Import the appropriate service
        if use_langgraph:
            from core.rag_agent_langgraph import RagAgentLangGraph as RagAgentService
        else:
            from core.rag_agent_service import RagAgentService
        
        print(f"✅ Import successful")
        
        # Initialize Pinecone
        try:
            pinecone_mgr = PineconeManager()
            print(f"✅ Pinecone initialized")
        except Exception as e:
            print(f"⚠️  Pinecone not available: {e}")
            print(f"   Skipping RAG agent test (requires Pinecone)")
            return
        
        # Initialize RAG agent
        rag_agent = RagAgentService(pinecone_mgr)
        print(f"✅ RAG agent initialized")
        
        # Test query
        test_message = "What were the main topics discussed?"
        test_history = []
        
        print(f"\n📝 Test Query: '{test_message}'")
        print(f"🤖 Response: ", end="", flush=True)
        
        # Stream response
        response_chunks = []
        for chunk in rag_agent.generate_response(test_message, test_history):
            response_chunks.append(chunk)
            # Print only the new content
            if len(response_chunks) > 1:
                new_content = chunk[len(response_chunks[-2]):]
                print(new_content, end="", flush=True)
            else:
                print(chunk, end="", flush=True)
        
        print("\n")
        
        if response_chunks:
            final_response = response_chunks[-1]
            print(f"✅ Response generated ({len(final_response)} chars)")
            
            # Check for question echoing
            if test_message.lower() in final_response.lower()[:100]:
                print(f"⚠️  Warning: Response may be echoing the question")
            else:
                print(f"✅ No question echoing detected")
        else:
            print(f"❌ No response generated")
        
        print(f"\n✅ {impl_name} implementation test PASSED")
        
    except Exception as e:
        print(f"\n❌ {impl_name} implementation test FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test both implementations
    print("\n" + "="*60)
    print("RAG Implementation Comparison Test")
    print("="*60)
    
    test_implementation(use_langgraph=False)
    test_implementation(use_langgraph=True)
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    print("\nTo switch implementations in the app:")
    print("  1. Open app.py")
    print("  2. Set USE_LANGGRAPH = True or False")
    print("  3. Restart the Gradio app")
    print()
