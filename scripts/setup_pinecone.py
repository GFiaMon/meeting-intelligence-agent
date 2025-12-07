import pinecone
import os
from dotenv import load_dotenv

load_dotenv()

pinecone.init(
    api_key=os.getenv('PINECONE_API_KEY'),
    environment=os.getenv('PINECONE_ENVIRONMENT')
)

index_name = os.getenv('PINECONE_INDEX')
if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine'
    )
    print(f'Index {index_name} created')
else:
    print(f'Index {index_name} already exists')