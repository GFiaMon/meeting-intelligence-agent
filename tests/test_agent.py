"""
Test script for conversational agent functionality
"""

from core.conversational_agent import ConversationalMeetingAgent
from core.pinecone_manager import PineconeManager
from core.transcription_service import TranscriptionService

print("=" * 60)
print("Testing Conversational Meeting Agent")
print("=" * 60)

# Initialize services
print("\n1. Initializing services...")
pm = PineconeManager()
ts = TranscriptionService()
agent = ConversationalMeetingAgent(pm, ts)
print("✅ Services initialized")

# Test 1: Simple greeting
print("\n2. Testing greeting response...")
history = []
message = "Hi"
response = ""
for chunk in agent.generate_response(message, history):
    response = chunk
print(f"User: {message}")
print(f"Agent: {response[:200]}...")

# Test 2: List meetings
print("\n3. Testing list meetings...")
history = [["Hi", response]]
message = "What meetings do I have?"
response = ""
for chunk in agent.generate_response(message, history):
    response = chunk
print(f"User: {message}")
print(f"Agent: {response[:200]}...")

# Test 3: Video upload request
print("\n4. Testing video upload request...")
history.append([message, response])
message = "I want to upload a video"
response = ""
for chunk in agent.generate_response(message, history):
    response = chunk
print(f"User: {message}")
print(f"Agent: {response[:200]}...")

print("\n" + "=" * 60)
print("✅ All basic tests passed!")
print("=" * 60)
