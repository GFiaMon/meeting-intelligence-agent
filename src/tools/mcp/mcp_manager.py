"""
MCP Manager - Official LangChain Implementation

Based on official documentation:
https://github.com/langchain-ai/langchain-mcp-adapters

This module provides a clean interface for integrating MCP (Model Context Protocol)
servers with your LangChain agent.
"""

import os
import asyncio
from typing import List, Dict, Any
from langchain.tools import BaseTool


class MCPManager:
    """
    Manages MCP server connections using official LangChain adapters.
    
    This class wraps the MultiServerMCPClient from langchain-mcp-adapters
    to provide a simple interface for loading tools from multiple MCP servers.
    
    Example:
        >>> servers = {
        ...     "zoom": {
        ...         "command": "npx",
        ...         "args": ["-y", "@modelcontextprotocol/server-zoom"],
        ...         "transport": "stdio",
        ...         "env": {"ZOOM_API_KEY": "your-key"}
        ...     }
        ... }
        >>> manager = MCPManager(servers)
        >>> await manager.initialize()
        >>> tools = manager.get_tools()
    """
    
    def __init__(self, server_configs: Dict[str, Dict[str, Any]] = None):
        """
        Initialize MCP manager.
        
        Args:
            server_configs: Dictionary of server configurations.
                Format (official LangChain format):
                {
                    "server_name": {
                        "command": "npx",
                        "args": ["-y", "@mcp/server-package"],
                        "transport": "stdio",  # or "streamable_http"
                        "env": {"API_KEY": "value"}  # optional
                    }
                }
                
        Example:
            {
                "zoom": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-zoom"],
                    "transport": "stdio",
                    "env": {
                        "ZOOM_API_KEY": os.getenv("ZOOM_API_KEY"),
                        "ZOOM_API_SECRET": os.getenv("ZOOM_API_SECRET")
                    }
                },
                "notion": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-notion"],
                    "transport": "stdio",
                    "env": {
                        "NOTION_API_KEY": os.getenv("NOTION_API_KEY")
                    }
                }
            }
        """
        self.server_configs = server_configs or {}
        self.client = None
        self.tools = []
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize MCP client and load all tools from configured servers.
        
        This method:
        1. Creates a MultiServerMCPClient with the server configs
        2. Calls get_tools() to load all tools from all servers
        3. Stores the tools for later use
        
        Returns:
            bool: True if initialization successful, False otherwise
            
        Raises:
            ImportError: If langchain-mcp-adapters is not installed
            Exception: If MCP initialization fails
        """
        if self._initialized:
            print("⚠️  MCP already initialized")
            return True
        
        if not self.server_configs:
            print("⚠️  No MCP servers configured")
            return False
        
        try:
            # Import here to provide better error message if not installed
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            print(f"🔌 Initializing MCP with {len(self.server_configs)} servers...")
            
            # Create multi-server client (official pattern)
            self.client = MultiServerMCPClient(self.server_configs)
            
            # Get all tools from all servers
            # This automatically handles:
            # - Starting server processes
            # - Establishing connections
            # - Loading tool definitions
            # - Converting to LangChain format
            self.tools = await self.client.get_tools()
            
            self._initialized = True
            
            print(f"✅ MCP initialized successfully!")
            print(f"   Loaded {len(self.tools)} tools from {len(self.server_configs)} servers:")
            for tool in self.tools:
                print(f"   - {tool.name}: {tool.description[:60]}...")
            
            return True
            
        except ImportError as e:
            print(f"❌ MCP dependencies not installed: {e}")
            print("   Install with: pip install langchain-mcp-adapters")
            return False
            
        except Exception as e:
            print(f"❌ MCP initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all loaded MCP tools in LangChain format.
        
        These tools can be:
        - Bound to LLMs via .bind_tools()
        - Used in LangGraph ToolNode
        - Combined with other LangChain tools
        
        Returns:
            List[BaseTool]: List of LangChain-compatible tools
            
        Example:
            >>> tools = manager.get_tools()
            >>> llm = ChatOpenAI().bind_tools(tools)
        """
        if not self._initialized:
            print("⚠️  MCP not initialized - call initialize() first")
            return []
        
        return self.tools
    
    async def close(self):
        """
        Close all MCP server connections.
        
        Note: MultiServerMCPClient handles cleanup automatically,
        but this method is provided for explicit cleanup if needed.
        """
        if self.client:
            # MultiServerMCPClient manages its own lifecycle
            pass
        
        self._initialized = False
        self.tools = []
    
    def is_initialized(self) -> bool:
        """Check if MCP is initialized."""
        return self._initialized
    
    def get_server_names(self) -> List[str]:
        """Get list of configured server names."""
        return list(self.server_configs.keys())
    
    def get_tool_count(self) -> int:
        """Get number of loaded tools."""
        return len(self.tools)


# ============================================================
# EXAMPLE USAGE
# ============================================================

async def example_usage():
    """
    Example demonstrating the official LangChain MCP pattern.
    """
    print("=" * 60)
    print("MCP Manager - Official LangChain Pattern")
    print("=" * 60)
    
    # Configure servers (official format)
    servers = {
        "zoom": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-zoom"],
            "transport": "stdio",
            "env": {
                "ZOOM_API_KEY": os.getenv("ZOOM_API_KEY", "demo-key"),
                "ZOOM_API_SECRET": os.getenv("ZOOM_API_SECRET", "demo-secret")
            }
        },
        "notion": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-notion"],
            "transport": "stdio",
            "env": {
                "NOTION_TOKEN": os.getenv("NOTION_TOKEN")
            }
        }
    }
    
    # Create manager
    manager = MCPManager(servers)
    
    # Initialize and load tools
    success = await manager.initialize()
    
    if success:
        # Get tools
        tools = manager.get_tools()
        
        print(f"\n📊 Loaded Tools ({len(tools)}):")
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   Description: {tool.description}")
        
        # Example: Use with LangChain
        print("\n" + "=" * 60)
        print("Integration Example:")
        print("=" * 60)
        print("""
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Get MCP tools
mcp_tools = manager.get_tools()

# Combine with your existing tools
all_tools = standard_tools + mcp_tools

# Bind to LLM
llm = ChatOpenAI(model="gpt-4").bind_tools(all_tools)

# Or create agent
agent = create_react_agent(llm, all_tools)
        """)
    
    # Cleanup
    await manager.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
