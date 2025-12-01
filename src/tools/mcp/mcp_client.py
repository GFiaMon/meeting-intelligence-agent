"""
MCP Client Manager for Notion Integration

Manages connection to Notion MCP server and loads tools.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import List


class MCPClientManager:
    """Manages MCP server connections and tool loading."""
    
    def __init__(self, server_configs):
        """
        Initialize MCP client manager.
        
        Args:
            server_configs: Dictionary of server configurations
                Example:
                {
                    "notion": {
                        "command": "npx",
                        "args": ["-y", "@notionhq/notion-mcp-server"],
                        "transport": "stdio",
                        "env": {"NOTION_TOKEN": "your-key"}
                    }
                }
        """
        self.server_configs = server_configs
        self.client = None
        self.tools = []
        self._initialized = False
    
    async def initialize(self):
        """
        Initialize MCP client and load tools.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self._initialized:
            print("⚠️  MCP already initialized")
            return True
        
        if not self.server_configs:
            print("⚠️  No MCP servers configured")
            return False
        
        try:
            print(f"🔌 Initializing MCP with {len(self.server_configs)} server(s)...")
            
            # Create client
            self.client = MultiServerMCPClient(self.server_configs)
            
            # Get tools (no need to call connect() - it's automatic!)
            self.tools = await self.client.get_tools()
            
            self._initialized = True
            
            print(f"✅ MCP initialized! Loaded {len(self.tools)} tools")
            return True
            
        except Exception as e:
            print(f"❌ MCP initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_langchain_tools(self):
        """Get loaded MCP tools in LangChain format."""
        if not self._initialized:
            print("⚠️  MCP not initialized - call initialize() first")
            return []
        return self.tools
    
    async def close(self):
        """Close MCP connections."""
        self._initialized = False
        self.tools = []