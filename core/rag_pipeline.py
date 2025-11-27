from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def process_transcript_to_documents(transcript_text, speaker_data, meeting_id):
    """
    Process transcript text and speaker data into LangChain Documents.
    
    Args:
        transcript_text (str): The full transcript text.
        speaker_data (list): List of dictionaries containing segment info (text, start, end, speaker).
        meeting_id (str): Unique identifier for the meeting.
        
    Returns:
        list[Document]: List of processed LangChain Documents.
    """
    documents = []
    
    # If we have detailed speaker data (segments), use that to create rich documents
    if speaker_data:
        for segment in speaker_data:
            text = segment.get("text", "").strip()
            if not text:
                continue
                
            metadata = {
                "meeting_id": meeting_id,
                "speaker": segment.get("speaker", "UNKNOWN"),
                "start_time": segment.get("start", 0),
                "end_time": segment.get("end", 0),
                "type": "transcript_segment"
            }
            
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
            
        # We might want to split these if they are individually too large,
        # though usually whisper segments are short.
        # However, the user explicitly asked to use RecursiveCharacterTextSplitter.
        # So we will apply it to the documents we just created.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # split_documents will respect the existing metadata
        final_documents = text_splitter.split_documents(documents)
        
    else:
        # Fallback if no speaker data: split the raw text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        metadata = {
            "meeting_id": meeting_id,
            "type": "full_transcript_chunk"
        }
        
        final_documents = text_splitter.create_documents(
            texts=[transcript_text],
            metadatas=[metadata]
        )
    
    return final_documents
