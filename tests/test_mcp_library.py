import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_library_connection():
    print("🧪 Testing MultiServerMCPClient connection...")
    
    server_config = {
        "berlin_time": {
            "url": "http://127.0.0.1:7870/gradio_api/mcp",
            "transport": "sse"
        }
    }
    
    print(f"   Config: {server_config}")
    
    try:
        client = MultiServerMCPClient(server_config)
        print("   Client created. Fetching tools...")
        
        # This is where it hangs in the main app
        tools = await client.get_tools()
        
        print(f"   ✅ Success! Found {len(tools)} tools.")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_library_connection())
    except KeyboardInterrupt:
        print("\n   ⚠️ Interrupted by user (Hang detected)")
