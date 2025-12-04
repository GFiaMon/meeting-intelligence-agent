import json
from datetime import datetime
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings import Config

class MetadataExtractor:
    """
    Service to extract intelligent metadata from meeting transcripts using an LLM.
    Extracts: Title, Summary, Date, and Speaker Identities.
    """
    
    def __init__(self):
        # Use a cost-effective model for metadata extraction if possible
        # defaulting to the configured model
        self.llm = ChatOpenAI(
            model=Config.METADATA_MODEL,
            temperature=0, # Deterministic output
            openai_api_key=Config.OPENAI_API_KEY
        )
    
    def extract_metadata(self, transcript_text: str) -> Dict[str, Any]:
        """
        Analyze transcript to extract title, summary, date, and speaker mapping.
        """
        # Truncate transcript if too long to avoid token limits (e.g., first 15k chars)
        # usually enough for context
        analysis_text = transcript_text[:15000]
        
        system_prompt = """You are a Metadata Extraction Expert. Analyze the provided meeting transcript and extract the following information in JSON format:

1. "title": A concise, meaningful title for the meeting (e.g., "Q3 Marketing Strategy Review").
2. "summary": A brief 2-3 sentence summary of the meeting.
3. "meeting_date": The date the meeting likely took place, if mentioned (format: YYYY-MM-DD). If not explicitly mentioned, return null.
4. "speaker_mapping": A dictionary mapping generic speaker labels (SPEAKER_00, SPEAKER_01) to likely real names based on introductions or context. If unknown, leave empty.

Example Output:
{
    "title": "Project Alpha Kickoff",
    "summary": "The team discussed the timeline for Project Alpha. John assigned tasks to Sarah and Mike.",
    "meeting_date": "2023-10-12",
    "speaker_mapping": {
        "SPEAKER_00": "John Smith",
        "SPEAKER_01": "Sarah Jones"
    }
}
"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Transcript:\n{analysis_text}")
            ])
            
            # Parse JSON from response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            metadata = json.loads(content)
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            # Return safe defaults
            return {
                "title": "Untitled Meeting",
                "summary": "No summary available.",
                "meeting_date": None,
                "speaker_mapping": {}
            }

    def apply_speaker_mapping(self, transcript: str, mapping: Dict[str, str]) -> str:
        """
        Replace generic speaker labels with identified names in the transcript.
        """
        if not mapping:
            return transcript
            
        updated_transcript = transcript
        for generic, real_name in mapping.items():
            # Replace "SPEAKER_00" with "John Smith"
            # We handle common variations in formatting
            updated_transcript = updated_transcript.replace(generic, real_name)
            
        return updated_transcript
