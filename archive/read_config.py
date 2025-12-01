
import os

file_path = "/Users/guillermo/.gemini/antigravity/mcp_config.json"
try:
    with open(file_path, 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error: {e}")
