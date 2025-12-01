"""
Test Agent with Notion MCP Integration

This script tests that the conversational agent loads Notion tools correctly.
"""

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Check prerequisites
print("=" * 70)
print("Testing Agent with Notion MCP Integration")
print("=" * 70)

# Check environment variables
print("\n1. Checking environment variables...")
enable_mcp = os.getenv("ENABLE_MCP", "false")
notion_key = os.getenv("NOTION_API_KEY", "")

print(f"   ENABLE_MCP: {enable_mcp}")
print(f"   NOTION_API_KEY: {'✅ Set' if notion_key else '❌ Not set'}")

if enable_mcp != "true":
    print("\n⚠️  ENABLE_MCP is not set to 'true'")
    print("   Add to .env: ENABLE_MCP=true")
    exit(1)

if not notion_key:
    print("\n❌ NOTION_API_KEY is not set!")
    print("   Add to .env: NOTION_API_KEY=your_integration_secret")
    exit(1)

# Import agent components
print("\n2. Importing agent components...")
try:
    from core.pinecone_manager import PineconeManager
    from core.transcription_service import TranscriptionService
    from core.conversational_agent import ConversationalMeetingAgent
    print("   ✅ Imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Initialize services
print("\n3. Initializing services...")
try:
    # Initialize Pinecone
    pinecone_mgr = PineconeManager()
    print("   ✅ Pinecone initialized")
    
    # Initialize transcription service
    transcription_svc = TranscriptionService()
    print("   ✅ Transcription service initialized")
    
except Exception as e:
    print(f"   ❌ Service initialization failed: {e}")
    exit(1)

# Initialize agent (this will load MCP tools)
print("\n4. Initializing agent with MCP tools...")
print("   (This may take a moment - downloading Notion MCP server)")
try:
    agent = ConversationalMeetingAgent(pinecone_mgr, transcription_svc)
    print("   ✅ Agent initialized")
except Exception as e:
    print(f"   ❌ Agent initialization failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Check tools
print("\n5. Checking loaded tools...")
print(f"   Total tools: {len(agent.tools)}")

# Count tool types
standard_tool_count = 0
notion_tool_count = 0

for tool in agent.tools:
    if "notion" in tool.name.lower() or "API-" in tool.name:
        notion_tool_count += 1
    else:
        standard_tool_count += 1

print(f"   Standard tools: {standard_tool_count}")
print(f"   Notion MCP tools: {notion_tool_count}")

if notion_tool_count > 0:
    print("\n✅ SUCCESS! Notion MCP tools are integrated!")
    print("\nSome Notion tools available:")
    notion_tools = [t for t in agent.tools if "API-" in t.name]
    for i, tool in enumerate(notion_tools[:5], 1):
        print(f"   {i}. {tool.name}")
    if len(notion_tools) > 5:
        print(f"   ... and {len(notion_tools) - 5} more")
else:
    print("\n⚠️  No Notion tools loaded!")
    print("   Check the error messages above")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
print("\nNext steps:")
print("1. Make sure your Notion integration has access to pages")
print("   (Click '...' on page → 'Add connections' → Select integration)")
print("2. Start your agent: python app_experiment_3.py")
print("3. Try: 'Export meeting summary to Notion'")
