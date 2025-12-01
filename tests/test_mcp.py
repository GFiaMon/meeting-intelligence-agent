"""
Test MCP Integration

This script tests the MCP manager implementation using the official
LangChain MCP adapters pattern.

Usage:
    1. Set environment variables in .env:
       ENABLE_MCP=true
       ZOOM_API_KEY=your_key
       ZOOM_API_SECRET=your_secret
       NOTION_API_KEY=your_token
    
    2. Run: python test_mcp.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_mcp_manager():
    """Test the MCPManager class."""
    print("=" * 70)
    print("Testing MCP Manager (Official LangChain Pattern)")
    print("=" * 70)
    
    try:
        from core.mcp_manager import MCPManager
        
        # Configure servers (official format)
        servers = {
            "zoom": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-zoom"],
                "transport": "stdio",
                "env": {
                    "ZOOM_API_KEY": os.getenv("ZOOM_API_KEY", ""),
                    "ZOOM_API_SECRET": os.getenv("ZOOM_API_SECRET", "")
                }
            },
            "notion": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-notion"],
                "transport": "stdio",
                "env": {
                    "NOTION_API_KEY": os.getenv("NOTION_API_KEY", "")
                }
            }
        }
        
        # Filter out servers without API keys
        active_servers = {
            name: config 
            for name, config in servers.items()
            if all(config.get("env", {}).values())
        }
        
        if not active_servers:
            print("\n⚠️  No API keys configured!")
            print("\nTo test MCP integration, add to your .env file:")
            print("  ZOOM_API_KEY=your_zoom_api_key")
            print("  ZOOM_API_SECRET=your_zoom_api_secret")
            print("  NOTION_API_KEY=your_notion_integration_token")
            return
        
        print(f"\n📋 Testing with {len(active_servers)} server(s):")
        for name in active_servers:
            print(f"  - {name}")
        
        # Create manager
        manager = MCPManager(active_servers)
        
        # Initialize
        print("\n🔄 Initializing MCP...")
        success = await manager.initialize()
        
        if success:
            # Get tools
            tools = manager.get_tools()
            
            print(f"\n✅ Success! Loaded {len(tools)} tools:\n")
            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name}")
                print(f"   Description: {tool.description}")
                print(f"   Args: {tool.args}")
                print()
            
            # Show integration example
            print("=" * 70)
            print("Integration Example:")
            print("=" * 70)
            print("""
# In your conversational_agent.py:

from core.mcp_manager import MCPManager
from config import Config
import asyncio

# Initialize MCP
mcp_manager = MCPManager(Config.MCP_SERVERS)
asyncio.run(mcp_manager.initialize())
mcp_tools = mcp_manager.get_tools()

# Combine with existing tools
all_tools = self.standard_tools + mcp_tools

# Bind to LLM
self.llm = ChatOpenAI(...).bind_tools(all_tools)
            """)
            
            # Cleanup
            await manager.close()
            print("\n✅ Test completed successfully!")
            
        else:
            print("\n❌ MCP initialization failed")
            print("\nTroubleshooting:")
            print("  1. Check that Node.js is installed: node --version")
            print("  2. Check API keys in .env file")
            print("  3. Try running manually: npx -y @modelcontextprotocol/server-zoom --help")
    
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\nInstall dependencies:")
        print("  pip install langchain-mcp-adapters")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_direct_client():
    """Test using MultiServerMCPClient directly (official example)."""
    print("\n" + "=" * 70)
    print("Testing Direct MultiServerMCPClient (Official Pattern)")
    print("=" * 70)
    
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # Simple test with one server
        servers = {
            "zoom": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-zoom"],
                "transport": "stdio",
                "env": {
                    "ZOOM_API_KEY": os.getenv("ZOOM_API_KEY", ""),
                    "ZOOM_API_SECRET": os.getenv("ZOOM_API_SECRET", "")
                }
            }
        }
        
        if not all(servers["zoom"]["env"].values()):
            print("\n⚠️  Skipping - no Zoom API keys configured")
            return
        
        print("\n🔄 Creating MultiServerMCPClient...")
        client = MultiServerMCPClient(servers)
        
        print("🔄 Loading tools...")
        tools = await client.get_tools()
        
        print(f"\n✅ Loaded {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}")
        
    except ImportError:
        print("\n⚠️  Skipping - langchain-mcp-adapters not installed")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("\n🧪 MCP Integration Test Suite\n")
    
    # Test 1: MCPManager class
    asyncio.run(test_mcp_manager())
    
    # Test 2: Direct client (optional)
    asyncio.run(test_direct_client())
    
    print("\n" + "=" * 70)
    print("Test suite completed!")
    print("=" * 70)
