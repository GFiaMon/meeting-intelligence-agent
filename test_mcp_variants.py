import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_url(url):
    print(f"\n🧪 Testing URL: {url}")
    server_config = {
        "test": {
            "url": url,
            "transport": "sse"
        }
    }
    
    try:
        # Set a timeout for the connection attempt
        client = MultiServerMCPClient(server_config)
        print("   Client created. Fetching tools (5s timeout)...")
        
        # We wrap get_tools in wait_for to avoid infinite hanging
        tools = await asyncio.wait_for(client.get_tools(), timeout=5.0)
        
        print(f"   ✅ SUCCESS! Found {len(tools)} tools.")
        return True
            
    except asyncio.TimeoutError:
        print("   ❌ TIMEOUT: Connection hung.")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

async def main():
    urls = [
        "http://127.0.0.1:7870/gradio_api/mcp",        # Current
        "http://127.0.0.1:7870/gradio_api/mcp/sse",    # Explicit SSE
        "http://127.0.0.1:7870/gradio_api/mcp/",       # Trailing slash
    ]
    
    for url in urls:
        if await test_url(url):
            print(f"\n🎉 FOUND WORKING URL: {url}")
            break

if __name__ == "__main__":
    asyncio.run(main())
