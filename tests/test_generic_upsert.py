import unittest
from unittest.mock import MagicMock, patch
from src.tools.general import upsert_text_to_pinecone, initialize_tools

class TestGenericUpsert(unittest.TestCase):
    def setUp(self):
        self.mock_pinecone_manager = MagicMock()
        initialize_tools(self.mock_pinecone_manager)

    @patch('src.tools.general.process_transcript_to_documents')
    def test_upsert_text_to_pinecone(self, mock_process):
        # Setup
        text = "This is a test document."
        title = "Test Doc"
        source = "Manual Entry"
        
        # Mock return value of process_transcript_to_documents
        mock_docs = [MagicMock()]
        mock_process.return_value = mock_docs
        
        # Execute
        result = upsert_text_to_pinecone.invoke({"text": text, "title": title, "source": source})
        
        # Verify
        self.assertTrue("Successfully saved" in result)
        self.mock_pinecone_manager.upsert_documents.assert_called_once()
        args, kwargs = self.mock_pinecone_manager.upsert_documents.call_args
        self.assertEqual(args[0], mock_docs)
        self.assertEqual(kwargs['namespace'], "default")

if __name__ == '__main__':
    unittest.main()
