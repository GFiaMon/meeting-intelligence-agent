"""
Quick diagnostic script to check if metadata filtering is currently working.

This script:
1. Checks existing data in Pinecone
2. Shows what metadata fields are available
3. Tests a simple filter query
4. Provides recommendations

Run this BEFORE running the full test suite to understand current state.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from core.pinecone_manager import PineconeManager


def diagnose_pinecone_filtering():
    """Run diagnostic checks on Pinecone filtering."""
    
    print("\n" + "="*80)
    print("PINECONE METADATA FILTERING DIAGNOSTIC")
    print("="*80 + "\n")
    
    # Step 1: Connect to Pinecone
    print("Step 1: Connecting to Pinecone...")
    try:
        pinecone_mgr = PineconeManager()
        print(f"✅ Connected to index: {pinecone_mgr.index_name}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Step 2: Check index stats
    print("\nStep 2: Checking index statistics...")
    try:
        stats = pinecone_mgr.index.describe_index_stats()
        print(f"✅ Index stats retrieved")
        print(f"   Total vectors: {stats.total_vector_count}")
        print(f"   Namespaces: {list(stats.namespaces.keys()) if stats.namespaces else 'None'}")
        
        if stats.namespaces:
            for ns, ns_stats in stats.namespaces.items():
                print(f"   - {ns}: {ns_stats.vector_count} vectors")
        
        if stats.total_vector_count == 0:
            print("\n⚠️  WARNING: No vectors in index!")
            print("   You need to upload some meeting transcripts first.")
            print("   Use the Gradio app to transcribe and upload a video.")
            return
            
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return
    
    # Step 3: Sample a few vectors to see metadata
    print("\nStep 3: Sampling vectors to inspect metadata...")
    try:
        from utils.embedding_utils import get_embedding_model
        
        embeddings = get_embedding_model()
        
        # Create a dummy query
        query_text = "meeting"
        query_embedding = embeddings.embed_query(query_text)
        
        # Query without filter to see what's there
        response = pinecone_mgr.index.query(
            namespace="default",  # Adjust if you use different namespace
            vector=query_embedding,
            top_k=3,
            include_metadata=True
        )
        
        if response.matches:
            print(f"✅ Retrieved {len(response.matches)} sample vectors")
            
            for i, match in enumerate(response.matches, 1):
                print(f"\n   Sample {i}:")
                print(f"   - Score: {match.score:.4f}")
                print(f"   - Metadata keys: {list(match.metadata.keys())}")
                
                # Check for important metadata fields
                important_fields = ["meeting_id", "meeting_date", "start_time", "end_time", "speaker"]
                present_fields = [f for f in important_fields if f in match.metadata]
                missing_fields = [f for f in important_fields if f not in match.metadata]
                
                if present_fields:
                    print(f"   - Present fields: {present_fields}")
                    for field in present_fields:
                        print(f"     • {field}: {match.metadata[field]}")
                
                if missing_fields:
                    print(f"   - Missing fields: {missing_fields}")
            
            # Check if meeting_id exists
            has_meeting_id = any("meeting_id" in m.metadata for m in response.matches)
            
            if has_meeting_id:
                print("\n✅ meeting_id field found in metadata!")
                
                # Get a sample meeting_id
                sample_meeting_id = None
                for match in response.matches:
                    if "meeting_id" in match.metadata:
                        sample_meeting_id = match.metadata["meeting_id"]
                        break
                
                if sample_meeting_id:
                    print(f"   Sample meeting_id: {sample_meeting_id}")
                    
                    # Step 4: Test filtering with this meeting_id
                    print(f"\nStep 4: Testing filter with meeting_id='{sample_meeting_id}'...")
                    
                    filter_dict = {"meeting_id": sample_meeting_id}
                    
                    filtered_response = pinecone_mgr.index.query(
                        namespace="default",
                        vector=query_embedding,
                        top_k=5,
                        filter=filter_dict,
                        include_metadata=True
                    )
                    
                    print(f"   Results with filter: {len(filtered_response.matches)}")
                    
                    if filtered_response.matches:
                        print(f"   ✅ Filter returned results!")
                        
                        # Verify all results have the correct meeting_id
                        all_correct = all(
                            m.metadata.get("meeting_id") == sample_meeting_id 
                            for m in filtered_response.matches
                        )
                        
                        if all_correct:
                            print(f"   ✅ All results have correct meeting_id!")
                            print(f"\n🎉 METADATA FILTERING IS WORKING!")
                        else:
                            print(f"   ❌ Some results have wrong meeting_id")
                            print(f"\n❌ METADATA FILTERING IS NOT WORKING CORRECTLY")
                    else:
                        print(f"   ⚠️  Filter returned no results")
                        print(f"   This could mean:")
                        print(f"   - Filter syntax is wrong")
                        print(f"   - meeting_id value doesn't match exactly")
                        print(f"   - There's only one meeting in the index")
                
            else:
                print("\n❌ meeting_id field NOT found in metadata!")
                print("   Your documents may not have been uploaded with metadata.")
                print("   Check your rag_pipeline.py implementation.")
        
        else:
            print("⚠️  No vectors returned from query")
            
    except Exception as e:
        print(f"❌ Error during metadata inspection: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Test LangChain retriever with filter
    print("\nStep 5: Testing LangChain retriever with filter...")
    try:
        if has_meeting_id and sample_meeting_id:
            retriever = pinecone_mgr.get_retriever(
                namespace="default",
                search_kwargs={
                    "k": 5,
                    "filter": {"meeting_id": sample_meeting_id}
                }
            )
            
            docs = retriever.invoke("What was discussed?")
            
            print(f"   ✅ LangChain retriever returned {len(docs)} documents")
            
            if docs:
                # Check if all docs have correct meeting_id
                all_correct = all(
                    doc.metadata.get("meeting_id") == sample_meeting_id 
                    for doc in docs
                )
                
                if all_correct:
                    print(f"   ✅ All documents have correct meeting_id!")
                    print(f"\n🎉 LANGCHAIN FILTERING IS WORKING!")
                else:
                    print(f"   ❌ Some documents have wrong meeting_id")
                    for doc in docs:
                        print(f"      - {doc.metadata.get('meeting_id')}")
            else:
                print(f"   ⚠️  No documents returned")
        
    except Exception as e:
        print(f"❌ LangChain retriever test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Final recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80 + "\n")
    
    if has_meeting_id and sample_meeting_id:
        print("✅ Your Pinecone index has meeting_id metadata")
        print("✅ You can proceed with metadata filtering")
        print("\nNext steps:")
        print("1. Run the full test suite: python tests/test_metadata_filtering.py")
        print("2. Test with real queries in the Gradio app")
        print("3. Try queries like: 'Summarize meeting_abc12345'")
    else:
        print("⚠️  Your Pinecone index may not have proper metadata")
        print("\nNext steps:")
        print("1. Upload a new meeting transcript using the Gradio app")
        print("2. Verify that rag_pipeline.py is adding metadata correctly")
        print("3. Run this diagnostic again")


if __name__ == "__main__":
    diagnose_pinecone_filtering()
