"""
MCP Client Manager - Example Implementation

This module demonstrates how to integrate MCP (Model Context Protocol) servers
with your LangChain-based meeting intelligence agent.

Usage:
    1. Install dependencies: pip install langchain-mcp-adapters mcp
    2. Configure MCP servers in config.py
    3. Initialize MCPClientManager in your agent
    4. Get LangChain-compatible tools via get_langchain_tools()
"""

import asyncio
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool


class MCPClientManager:
    """
    Manages connections to MCP servers and converts their tools to LangChain format.
    
    MCP (Model Context Protocol) is a standardized way to connect AI applications
    to external tools and data sources. This manager:
    - Connects to multiple MCP servers (Zoom, Notion, etc.)
    - Loads tools from each server
    - Converts them to LangChain-compatible format
    - Manages server lifecycle (connect/disconnect)
    
    Example:
        >>> server_configs = [
        ...     {
        ...         "name": "zoom",
        ...         "transport": "stdio",
        ...         "command": "npx",
        ...         "args": ["-y", "@modelcontextprotocol/server-zoom"],
        ...         "env": {"ZOOM_API_KEY": "your-key"}
        ...     }
        ... ]
        >>> manager = MCPClientManager(server_configs)
        >>> await manager.initialize()
        >>> tools = manager.get_langchain_tools()
    """
    
    def __init__(self, server_configs: List[Dict[str, Any]] = None):
        """
        Initialize MCP client manager.
        
        Args:
            server_configs: List of server configuration dictionaries.
                Each config should have:
                - name (str): Server identifier (e.g., "zoom", "notion")
                - transport (str): Communication method ("stdio" or "sse")
                - command (str): Command to start server (e.g., "npx")
                - args (List[str]): Command arguments
                - env (Dict[str, str], optional): Environment variables
                
        Example config:
            [
                {
                    "name": "zoom",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-zoom"],
                    "env": {
                        "ZOOM_API_KEY": "your-zoom-api-key",
                        "ZOOM_API_SECRET": "your-zoom-api-secret"
                    }
                },
                {
                    "name": "notion",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-notion"],
                    "env": {
                        "NOTION_API_KEY": "your-notion-integration-token"
                    }
                }
            ]
        """
        self.server_configs = server_configs or []
        self.client = None
        self.tools = []
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize MCP client and load tools from all configured servers.
        
        This method:
        1. Creates a MultiServerMCPClient
        2. Connects to all configured MCP servers
        3. Loads tools from each server
        4. Converts tools to LangChain format
        
        Returns:
            bool: True if initialization successful, False otherwise
            
        Raises:
            Exception: If MCP client initialization fails
        """
        if self._initialized:
            print("⚠️  MCP client already initialized")
            return True
            
        if not self.server_configs:
            print("⚠️  No MCP servers configured - skipping MCP initialization")
            return False
        
        try:
            # Import here to avoid dependency issues if not installed
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            print(f"🔌 Initializing MCP client with {len(self.server_configs)} servers...")
            
            # Create multi-server client
            self.client = MultiServerMCPClient(self.server_configs)
            
            # Connect to all servers
            await self.client.connect()
            print("✅ Connected to MCP servers")
            
            # Get all tools from all servers
            self.tools = await self.client.get_tools()
            
            self._initialized = True
            
            print(f"✅ MCP Client initialized successfully!")
            print(f"   Loaded {len(self.tools)} tools from {len(self.server_configs)} servers:")
            
            # Log available tools
            for tool in self.tools:
                print(f"   - {tool.name}: {tool.description[:60]}...")
            
            return True
            
        except ImportError as e:
            print(f"❌ MCP dependencies not installed: {e}")
            print("   Install with: pip install langchain-mcp-adapters mcp")
            self.tools = []
            return False
            
        except Exception as e:
            print(f"❌ Error initializing MCP client: {e}")
            import traceback
            print(traceback.format_exc())
            self.tools = []
            return False
    
    def get_langchain_tools(self) -> List[BaseTool]:
        """
        Get all MCP tools converted to LangChain-compatible format.
        
        These tools can be directly used with LangChain agents:
        - Bound to LLMs via .bind_tools()
        - Used in LangGraph ToolNode
        - Invoked by agents during reasoning
        
        Returns:
            List[BaseTool]: List of LangChain-compatible tools
            
        Example:
            >>> tools = manager.get_langchain_tools()
            >>> llm = ChatOpenAI().bind_tools(tools)
        """
        if not self._initialized:
            print("⚠️  MCP client not initialized - call initialize() first")
            return []
        
        return self.tools
    
    async def close(self):
        """
        Close all MCP server connections and cleanup resources.
        
        Always call this when shutting down to properly close connections.
        
        Example:
            >>> await manager.close()
        """
        if self.client:
            try:
                await self.client.close()
                print("✅ MCP client connections closed")
            except Exception as e:
                print(f"⚠️  Error closing MCP client: {e}")
        
        self._initialized = False
        self.tools = []
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of all available tool names.
        
        Returns:
            List[str]: List of tool names
        """
        return [tool.name for tool in self.tools]
    
    def get_server_count(self) -> int:
        """
        Get number of configured MCP servers.
        
        Returns:
            int: Number of servers
        """
        return len(self.server_configs)
    
    def is_initialized(self) -> bool:
        """
        Check if MCP client is initialized.
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized


# ============================================================
# EXAMPLE USAGE
# ============================================================

async def example_usage():
    """
    Example demonstrating how to use MCPClientManager.
    """
    print("=" * 60)
    print("MCP Client Manager - Example Usage")
    print("=" * 60)
    
    # Example server configurations
    server_configs = [
        {
            "name": "zoom",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-zoom"],
            "env": {
                "ZOOM_API_KEY": "your-zoom-api-key",
                "ZOOM_API_SECRET": "your-zoom-api-secret"
            }
        },
        {
            "name": "notion",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-notion"],
            "env": {
                "NOTION_API_KEY": "your-notion-integration-token"
            }
        }
    ]
    
    # Create MCP client manager
    manager = MCPClientManager(server_configs)
    
    # Initialize and load tools
    success = await manager.initialize()
    
    if success:
        # Get LangChain-compatible tools
        tools = manager.get_langchain_tools()
        
        print(f"\n📊 Available Tools ({len(tools)}):")
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   Description: {tool.description}")
            print(f"   Args: {tool.args}")
        
        # Example: Use with LangChain LLM
        print("\n" + "=" * 60)
        print("Integration with LangChain LLM:")
        print("=" * 60)
        print("""
from langchain_openai import ChatOpenAI

# Bind tools to LLM
llm = ChatOpenAI(model="gpt-4").bind_tools(tools)

# Use in agent
from langgraph.prebuilt import ToolNode
tool_node = ToolNode(tools)
        """)
    
    # Cleanup
    await manager.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
