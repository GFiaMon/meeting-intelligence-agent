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
        """
        self.server_configs = server_configs
        self.clients = []  # List of active clients
        self.tools = []
        self._initialized = False
    
    async def initialize(self):
        """
        Initialize MCP clients and load tools sequentially.
        
        Returns:
            bool: True if at least one server initialized successfully
        """
        if self._initialized:
            print("⚠️  MCP already initialized")
            return True
        
        if not self.server_configs:
            print("⚠️  No MCP servers configured")
            return False
        
        print(f"🔌 Initializing {len(self.server_configs)} MCP server(s) sequentially...")
        
        success_count = 0
        
        # Iterate through each server config and initialize separately
        for server_name, config in self.server_configs.items():
            try:
                print(f"   • Connecting to '{server_name}'...")
                
                # Create a client for just this server
                # We wrap it in a single-entry dict because MultiServerMCPClient expects a dict
                single_server_config = {server_name: config}
                client = MultiServerMCPClient(single_server_config)
                
                # Connect and get tools
                # This will only block for this specific server
                server_tools = await client.get_tools()
                
                # Store successful client and tools
                self.clients.append(client)
                self.tools.extend(server_tools)
                
                print(f"   ✅ '{server_name}' connected! Loaded {len(server_tools)} tools")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to connect to '{server_name}': {e}")
                # We continue to the next server instead of failing everything
                continue
        
        self._initialized = True
        
        if success_count > 0:
            print(f"✅ MCP initialization complete. Total tools loaded: {len(self.tools)}")
            return True
        else:
            print("❌ MCP initialization failed: No servers connected successfully")
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
        
        # Close all clients
        # Note: MultiServerMCPClient might not have an explicit close method exposed easily,
        # but we clear references. The underlying connections should be cleaned up by GC or context managers.
        self.clients = []