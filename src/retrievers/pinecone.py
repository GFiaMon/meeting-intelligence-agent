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

    def upsert_documents(self, documents, namespace):
        """
        Upsert LangChain Document objects into the Pinecone index.
        """
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

    def get_retriever(self, namespace, search_kwargs=None):
        """
        Returns a LangChain retriever for the specified namespace.
        """
        if search_kwargs is None:
            search_kwargs = {"k": 5}

        vectorstore = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            namespace=namespace,
            pinecone_api_key=self.api_key
        )
        
        return vectorstore.as_retriever(search_kwargs=search_kwargs)