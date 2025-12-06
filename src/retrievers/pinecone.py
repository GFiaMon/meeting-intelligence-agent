import os
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from src.config.settings import Config
from src.utils.embedding import get_embedding_model

class PineconeManager:
    def __init__(self, index_name=None):
        """
        Initialize Pinecone client and connect to the index.
        Creates the index if it doesn't exist.
        """
        self.api_key = Config.PINECONE_API_KEY
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
            
        self.pc = Pinecone(api_key=self.api_key)
        self.index_name = index_name or Config.PINECONE_INDEX
        
        # Check if index exists, create it if it doesn't
        try:
            existing_indexes = [i.name for i in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                print(f"Index '{self.index_name}' does not exist. Creating it now...")
                
                # Create index with ServerlessSpec
                # OpenAI embeddings (text-embedding-ada-002) use dimension 1536
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric='cosine',  # Cosine similarity for semantic search
                    spec=ServerlessSpec(
                        cloud='aws',  # or 'gcp', 'azure'
                        region='us-east-1'  # adjust based on your preference
                    )
                )
                print(f"✅ Successfully created index '{self.index_name}'")
            else:
                print(f"✅ Connected to existing index '{self.index_name}'")
        except Exception as e:
            print(f"Error managing Pinecone index: {e}")
            raise e

        self.index = self.pc.Index(self.index_name)
        self.embeddings = get_embedding_model()

    def upsert_documents(self, documents, namespace=None):
        """
        Upsert LangChain Document objects into the Pinecone index.
        """
        if namespace is None:
            namespace = Config.PINECONE_NAMESPACE
        if not documents:
            print("No documents to upsert.")
            return

        try:
            # Using LangChain's PineconeVectorStore for easy upsert
            PineconeVectorStore.from_documents(
                documents=documents,
                embedding=self.embeddings,
                index_name=self.index_name,
                namespace=namespace,
                pinecone_api_key=self.api_key
            )
            print(f"Successfully upserted {len(documents)} documents to namespace '{namespace}'.")
        except Exception as e:
            print(f"Error upserting documents: {e}")
            raise e

    def get_retriever(self, namespace=None, search_kwargs=None):
        """
        Returns a LangChain retriever for the specified namespace.
        """
        if namespace is None:
            namespace = Config.PINECONE_NAMESPACE
        if search_kwargs is None:
            search_kwargs = {"k": 5}

        vectorstore = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            namespace=namespace,
            pinecone_api_key=self.api_key
        )
        
        return vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    def delete_by_meeting_id(self, meeting_id: str, namespace: str = None):
        """
        Delete all vectors associated with a specific meeting_id.
        
        Args:
            meeting_id: The meeting ID to delete (e.g., "meeting_abc12345")
            namespace: The namespace to delete from (default: Config.PINECONE_NAMESPACE)
        """
        if namespace is None:
            namespace = Config.PINECONE_NAMESPACE
        try:
            # Pinecone allows deleting by filter directly
            # This is more efficient than query + delete
            delete_response = self.index.delete(
                filter={"meeting_id": {"$eq": meeting_id}},
                namespace=namespace
            )
            
            print(f"✅ Successfully deleted vectors for meeting_id: {meeting_id}")
            
            # Note: Pinecone's delete with filter doesn't return count
            # We'll return a success indicator
            return True
            
        except Exception as e:
            print(f"Error deleting vectors for meeting_id {meeting_id}: {e}")
            raise e
    
    def delete_namespace(self, namespace: str):
        """
        Delete ALL vectors in a specific namespace.
        WARNING: This deletes everything in the namespace!
        
        Args:
            namespace: The namespace to clear
        """
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            print(f"✅ Successfully deleted all vectors in namespace: {namespace}")
        except Exception as e:
            print(f"Error deleting namespace {namespace}: {e}")
            raise e
    
    def list_meetings(self, namespace: str = None, limit: int = 100):
        """
        List all unique meeting IDs stored in Pinecone.
        
        Args:
            namespace: The namespace to query (default: Config.PINECONE_NAMESPACE)
            limit: Maximum number of vectors to scan (default: 100)
            
        Returns:
            List of dictionaries with meeting metadata
        """
        if namespace is None:
            namespace = Config.PINECONE_NAMESPACE
        try:
            # Query random vectors to get metadata
            results = self.index.query(
                namespace=namespace,
                vector=[0.0] * 1536,  # Dummy vector
                top_k=limit,
                include_metadata=True
            )
            
            # Extract unique meetings
            meetings = {}
            for match in results.matches:
                metadata = match.metadata
                meeting_id = metadata.get("meeting_id")
                
                if meeting_id and meeting_id not in meetings:
                    meetings[meeting_id] = {
                        "meeting_id": meeting_id,
                        "meeting_date": metadata.get("meeting_date"),
                        "meeting_title": metadata.get("meeting_title", metadata.get("title", "Untitled Meeting")),
                        "meeting_duration": metadata.get("duration", metadata.get("meeting_duration", "N/A")),
                        "source_file": metadata.get("source_file", "N/A"),
                    }
            
            return list(meetings.values())  
            
        except Exception as e:
            print(f"Error listing meetings: {e}")
            return []