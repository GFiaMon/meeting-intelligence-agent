from langchain_openai import OpenAIEmbeddings
from src.config.settings import Config

def get_embedding_model():
    """
    Initialize and return the OpenAI Embeddings model.
    """
    return OpenAIEmbeddings(
        openai_api_key=Config.OPENAI_API_KEY,
        model="text-embedding-3-small"  # Using a cost-effective and performant model
    )
