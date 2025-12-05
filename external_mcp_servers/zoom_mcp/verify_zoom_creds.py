import os
import sys
import urllib.parse

# Add project root to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.config.settings import Config

def generate_install_url():
    print("🔍 Generating Zoom App Install URL...")
    
    client_id = Config.ZOOM_CLIENT_ID
    
    if not client_id:
        print("❌ Missing ZOOM_CLIENT_ID in .env or Config.")
        return

    # Base Authorization URL
    base_url = "https://zoom.us/oauth/authorize"
    
    # Parameters
    # Note: 'redirect_uri' must match exactly what is in the Zoom App Marketplace.
    # We'll assume the user might have set it to their ngrok URL or localhost.
    # If not provided in config, we'll leave it out or use a placeholder instruction.
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        # "redirect_uri": "YOUR_REDIRECT_URI" # Optional if only one is configured in Zoom
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print("\n✅ **Action Required**: Install the App")
    print("To authorize this app to receive webhooks for your meetings, you must install it.")
    print("1. Ensure your 'Redirect URL' in Zoom Marketplace matches your server (e.g., your ngrok URL).")
    print("2. Open the following URL in your browser:")
    print(f"\n👉 {url}\n")
    print("3. Log in and click 'Allow'.")
    print("4. Once installed, start the server (`python src/zoom_mcp/server.py`) and start a meeting.")

if __name__ == "__main__":
    generate_install_url()
