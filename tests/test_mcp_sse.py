import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test_mcp_sse():
    print("Testing MCP connection via SSE...")
    url = "http://localhost:7860/gradio_api/mcp/"
    print(f"Target URL: {url}")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                print("Connected! Initializing...")
                await session.initialize()
                print("Initialized! Listing tools...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"- {tool.name}: {tool.description}")
                    
                # Try calling it
                print("\nCalling get_berlin_time...")
                result = await session.call_tool("get_berlin_time", {})
                print(f"Result: {result}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_sse())
