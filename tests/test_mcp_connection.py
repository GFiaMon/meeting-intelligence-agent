import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp():
    print("Testing MCP connection...")
    
    script_path = os.path.abspath("external_mcp_servers/app_time_mcp_server.py")
    print(f"Target script: {script_path}")
    
    server_params = StdioServerParameters(
        command="python",
        args=[script_path],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
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
    asyncio.run(test_mcp())
