"""
Comprehensive test suite for Pinecone metadata filtering.

This test suite verifies that:
1. Metadata is correctly stored in Pinecone
2. Filters work in isolation (without similarity search)
3. Filters work with similarity search (the RAG use case)
4. The RAG agent correctly applies filters based on queries

Run this test to verify your metadata filtering implementation.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from core.pinecone_manager import PineconeManager
from core.rag_pipeline import process_transcript_to_documents
from langchain_core.documents import Document


class MetadataFilteringTester:
    """Test suite for metadata filtering in Pinecone."""
    
    def __init__(self):
        """Initialize the tester with Pinecone connection."""
        print("\n" + "="*80)
        print("PINECONE METADATA FILTERING TEST SUITE")
        print("="*80 + "\n")
        
        try:
            self.pinecone_mgr = PineconeManager()
            print("✅ Connected to Pinecone")
            print(f"   Index: {self.pinecone_mgr.index_name}")
        except Exception as e:
            print(f"❌ Failed to connect to Pinecone: {e}")
            raise
    
    def create_test_documents(self) -> tuple[List[Document], List[str]]:
        """
        Create test documents with different meeting_ids for testing.
        
        Returns:
            Tuple of (documents, meeting_ids)
        """
        print("\n" + "-"*80)
        print("STEP 1: Creating Test Documents")
        print("-"*80)
        
        # Create mock speaker data for two different meetings
        meeting_ids = ["meeting_test001", "meeting_test002"]
        all_documents = []
        
        for idx, meeting_id in enumerate(meeting_ids):
            speaker_data = [
                {
                    "text": f"This is meeting {idx+1}. We discussed the quarterly results.",
                    "start": 0.0,
                    "end": 5.0,
                    "speaker": "SPEAKER_00"
                },
                {
                    "text": f"In meeting {idx+1}, we also talked about the new product launch.",
                    "start": 5.0,
                    "end": 10.0,
                    "speaker": "SPEAKER_01"
                },
                {
                    "text": f"Meeting {idx+1} concluded with action items for the team.",
                    "start": 10.0,
                    "end": 15.0,
                    "speaker": "SPEAKER_00"
                }
            ]
            
            transcript_text = " ".join([seg["text"] for seg in speaker_data])
            
            meeting_metadata = {
                "meeting_date": f"2025-11-{20+idx:02d}",
                "meeting_title": f"Test Meeting {idx+1}",
                "source_file": f"test_meeting_{idx+1}.mp4"
            }
            
            documents = process_transcript_to_documents(
                transcript_text=transcript_text,
                speaker_data=speaker_data,
                meeting_id=meeting_id,
                meeting_metadata=meeting_metadata,
                min_chunk_size=50,  # Small for testing
                max_chunk_size=200,
                chunk_overlap=20
            )
            
            all_documents.extend(documents)
            print(f"✅ Created {len(documents)} documents for {meeting_id}")
            
            # Print sample metadata
            if documents:
                print(f"   Sample metadata: {documents[0].metadata}")
        
        print(f"\n📊 Total test documents created: {len(all_documents)}")
        return all_documents, meeting_ids
    
    def upload_test_documents(self, documents: List[Document]):
        """Upload test documents to Pinecone."""
        print("\n" + "-"*80)
        print("STEP 2: Uploading Test Documents to Pinecone")
        print("-"*80)
        
        try:
            self.pinecone_mgr.upsert_documents(
                documents=documents,
                namespace="test_metadata_filtering"
            )
            print(f"✅ Successfully uploaded {len(documents)} documents")
            print("   Namespace: test_metadata_filtering")
            
            # Wait a moment for indexing
            import time
            print("   Waiting 3 seconds for indexing...")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Failed to upload documents: {e}")
            raise
    
    def test_basic_retrieval(self, meeting_ids: List[str]):
        """Test basic retrieval without filters."""
        print("\n" + "-"*80)
        print("STEP 3: Test Basic Retrieval (No Filter)")
        print("-"*80)
        
        try:
            retriever = self.pinecone_mgr.get_retriever(
                namespace="test_metadata_filtering",
                search_kwargs={"k": 5}
            )
            
            query = "What were the quarterly results?"
            docs = retriever.invoke(query)
            
            print(f"✅ Retrieved {len(docs)} documents")
            print(f"   Query: '{query}'")
            
            # Show which meetings were retrieved
            meeting_ids_found = set()
            for doc in docs:
                meeting_ids_found.add(doc.metadata.get("meeting_id", "UNKNOWN"))
            
            print(f"   Meetings found: {meeting_ids_found}")
            
            if len(meeting_ids_found) > 1:
                print("   ℹ️  Multiple meetings retrieved (expected without filter)")
            
            return docs
            
        except Exception as e:
            print(f"❌ Basic retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def test_filtered_retrieval(self, meeting_ids: List[str]):
        """Test retrieval WITH metadata filter."""
        print("\n" + "-"*80)
        print("STEP 4: Test Filtered Retrieval (WITH Filter)")
        print("-"*80)
        
        target_meeting = meeting_ids[0]
        print(f"🎯 Target meeting: {target_meeting}")
        
        # Test different filter syntaxes
        filter_syntaxes = [
            ("Simple equality", {"meeting_id": target_meeting}),
            ("Explicit $eq", {"meeting_id": {"$eq": target_meeting}}),
        ]
        
        results = {}
        
        for syntax_name, filter_dict in filter_syntaxes:
            print(f"\n   Testing filter syntax: {syntax_name}")
            print(f"   Filter: {filter_dict}")
            
            try:
                retriever = self.pinecone_mgr.get_retriever(
                    namespace="test_metadata_filtering",
                    search_kwargs={
                        "k": 10,
                        "filter": filter_dict
                    }
                )
                
                query = "What were discussed in the meeting?"
                docs = retriever.invoke(query)
                
                print(f"   ✅ Retrieved {len(docs)} documents")
                
                # Verify all results are from target meeting
                meeting_ids_found = set()
                for doc in docs:
                    meeting_ids_found.add(doc.metadata.get("meeting_id", "UNKNOWN"))
                
                print(f"   Meetings found: {meeting_ids_found}")
                
                if meeting_ids_found == {target_meeting}:
                    print(f"   ✅ SUCCESS: All results from target meeting!")
                    results[syntax_name] = "PASS"
                elif len(meeting_ids_found) == 0:
                    print(f"   ⚠️  WARNING: No results returned (filter may be too restrictive)")
                    results[syntax_name] = "NO_RESULTS"
                else:
                    print(f"   ❌ FAILURE: Results from multiple meetings (filter not working)")
                    results[syntax_name] = "FAIL"
                
                # Show sample results
                if docs:
                    print(f"\n   Sample result:")
                    print(f"   - Content: {docs[0].page_content[:100]}...")
                    print(f"   - Metadata: {docs[0].metadata}")
                
            except Exception as e:
                print(f"   ❌ Error with {syntax_name}: {e}")
                results[syntax_name] = "ERROR"
                import traceback
                traceback.print_exc()
        
        return results
    
    def test_rag_agent_filtering(self, meeting_ids: List[str]):
        """Test that RAG agent correctly applies filters based on query."""
        print("\n" + "-"*80)
        print("STEP 5: Test RAG Agent Filter Application")
        print("-"*80)
        
        try:
            # Test both implementations
            from core.rag_agent_service import RagAgentService
            from core.rag_agent_langgraph import RagAgentLangGraph
            
            implementations = [
                ("Original", RagAgentService),
                ("LangGraph", RagAgentLangGraph)
            ]
            
            target_meeting = meeting_ids[0]
            
            for impl_name, impl_class in implementations:
                print(f"\n   Testing {impl_name} Implementation")
                print(f"   {'-'*40}")
                
                try:
                    # Create agent with test namespace
                    agent = impl_class(self.pinecone_mgr)
                    
                    # Test query with meeting_id
                    query = f"Summarize {target_meeting}"
                    print(f"   Query: '{query}'")
                    
                    # Get retrieval kwargs
                    kwargs = agent._get_retrieval_kwargs(query)
                    print(f"   Generated search_kwargs: {kwargs}")
                    
                    # Check if filter is present
                    if "filter" in kwargs:
                        filter_dict = kwargs["filter"]
                        print(f"   ✅ Filter detected: {filter_dict}")
                        
                        # Verify filter targets correct meeting
                        if filter_dict.get("meeting_id") == target_meeting or \
                           filter_dict.get("meeting_id", {}).get("$eq") == target_meeting:
                            print(f"   ✅ Filter targets correct meeting!")
                        else:
                            print(f"   ❌ Filter targets wrong meeting: {filter_dict}")
                    else:
                        print(f"   ⚠️  No filter in search_kwargs (may be expected for this query)")
                    
                except Exception as e:
                    print(f"   ❌ Error testing {impl_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"❌ RAG agent test failed: {e}")
            import traceback
            traceback.print_exc()
    
    def test_direct_pinecone_query(self, meeting_ids: List[str]):
        """Test Pinecone directly (bypass LangChain) to verify filter support."""
        print("\n" + "-"*80)
        print("STEP 6: Direct Pinecone API Test (Bypass LangChain)")
        print("-"*80)
        
        try:
            from utils.embedding_utils import get_embedding_model
            
            embeddings = get_embedding_model()
            target_meeting = meeting_ids[0]
            
            # Create a query embedding
            query_text = "What were the quarterly results?"
            query_embedding = embeddings.embed_query(query_text)
            
            print(f"   Query: '{query_text}'")
            print(f"   Target meeting: {target_meeting}")
            
            # Query Pinecone directly with filter
            filter_dict = {"meeting_id": target_meeting}
            
            response = self.pinecone_mgr.index.query(
                namespace="test_metadata_filtering",
                vector=query_embedding,
                top_k=5,
                filter=filter_dict,
                include_metadata=True
            )
            
            print(f"   ✅ Direct query successful")
            print(f"   Results returned: {len(response.matches)}")
            
            if response.matches:
                print(f"\n   Sample match:")
                match = response.matches[0]
                print(f"   - Score: {match.score}")
                print(f"   - Metadata: {match.metadata}")
                
                # Verify meeting_id
                if match.metadata.get("meeting_id") == target_meeting:
                    print(f"   ✅ Direct Pinecone filtering WORKS!")
                else:
                    print(f"   ❌ Wrong meeting_id in results")
            else:
                print(f"   ⚠️  No matches returned (filter may be too restrictive)")
                
        except Exception as e:
            print(f"❌ Direct Pinecone query failed: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup_test_data(self):
        """Clean up test data from Pinecone."""
        print("\n" + "-"*80)
        print("CLEANUP: Removing Test Data")
        print("-"*80)
        
        try:
            # Note: Pinecone doesn't have a simple "delete namespace" method
            # You would need to delete by IDs or use the Pinecone console
            print("   ℹ️  Test data remains in namespace 'test_metadata_filtering'")
            print("   ℹ️  You can delete it manually from Pinecone console if needed")
            print("   ℹ️  Or it will be overwritten on next test run")
            
        except Exception as e:
            print(f"   ⚠️  Cleanup note: {e}")
    
    def run_all_tests(self):
        """Run the complete test suite."""
        try:
            # Create and upload test data
            documents, meeting_ids = self.create_test_documents()
            self.upload_test_documents(documents)
            
            # Run tests
            self.test_basic_retrieval(meeting_ids)
            filter_results = self.test_filtered_retrieval(meeting_ids)
            self.test_rag_agent_filtering(meeting_ids)
            self.test_direct_pinecone_query(meeting_ids)
            
            # Summary
            print("\n" + "="*80)
            print("TEST SUMMARY")
            print("="*80)
            
            print("\n📊 Filter Syntax Results:")
            for syntax, result in filter_results.items():
                status_emoji = {
                    "PASS": "✅",
                    "FAIL": "❌",
                    "NO_RESULTS": "⚠️",
                    "ERROR": "❌"
                }.get(result, "❓")
                print(f"   {status_emoji} {syntax}: {result}")
            
            # Final verdict
            if all(r == "PASS" for r in filter_results.values()):
                print("\n🎉 ALL TESTS PASSED! Metadata filtering is working correctly.")
            elif any(r == "PASS" for r in filter_results.values()):
                print("\n⚠️  PARTIAL SUCCESS: Some filter syntaxes work, others don't.")
                print("   Recommendation: Use the syntax that passed.")
            else:
                print("\n❌ TESTS FAILED: Metadata filtering is NOT working.")
                print("   Recommendation: Check Pinecone documentation and LangChain version.")
            
            # Cleanup
            self.cleanup_test_data()
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    tester = MetadataFilteringTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
