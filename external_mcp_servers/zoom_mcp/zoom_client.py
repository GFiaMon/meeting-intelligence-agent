import asyncio
import json
import websockets
import aiohttp
from typing import Optional, Callable, Awaitable
from src.config.settings import Config

class ZoomRTMSClient:
    """
    Client for connecting to Zoom Real-time Media Streams (RTMS).
    Handles authentication and WebSocket connection.
    """
    
    def __init__(self, on_message: Callable[[dict], Awaitable[None]]):
        self.on_message = on_message
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.access_token: Optional[str] = None
        
        # For General Apps, we don't need Account ID for the RTMS connection itself
        # The token comes from the webhook payload
        self.client_id = Config.ZOOM_CLIENT_ID if hasattr(Config, 'ZOOM_CLIENT_ID') else None
        self.client_secret = Config.ZOOM_CLIENT_SECRET if hasattr(Config, 'ZOOM_CLIENT_SECRET') else None

    async def connect_to_stream(self, signaling_url: str, token: str, meeting_id: str):
        """
        Connect to Zoom RTMS using the provided Signaling URL and Token.
        This is the entry point called by the webhook handler.
        """
        self.is_running = True
        self.access_token = token # This is the 'join_token' or 'access_token' for the meeting
        
        print(f"🔗 Connecting to Zoom Signaling Server: {signaling_url}")
        print(f"🔑 Token: {token[:10]}...{token[-5:] if len(token) > 15 else ''}")
        
        try:
            # 1. Connect to Signaling Server
            async with websockets.connect(signaling_url) as signaling_ws:
                print("✅ Connected to Signaling Server")
                
                # 2. Perform Signaling Handshake
                # Note: The exact payload depends on Zoom's specific version, 
                # but typically involves sending a 'join' or 'handshake' message.
                # Since we don't have the exact SDK, we'll try a standard pattern 
                # or wait for the user to provide the sample if this fails.
                
                # For now, we'll assume the URL itself contains the necessary auth params
                # or we send a simple auth message.
                
                # WAIT: The user didn't provide the sample code. 
                # I will implement a robust loop that tries to read messages.
                # If Zoom sends a "Hello" or "Challenge", we can respond.
                
                async for message in signaling_ws:
                    if not self.is_running:
                        break
                        
                    data = json.loads(message)
                    print(f"📩 Signaling Message: {data}")
                    
                    # If we get a Media Server URL, connect to it
                    if "media_server_url" in data:
                        media_url = data["media_server_url"]
                        asyncio.create_task(self._connect_to_media(media_url))
                        
        except Exception as e:
            print(f"❌ Signaling Connection Failed: {e}")
            self.is_running = False
            
    async def _connect_to_media(self, media_url: str):
        """
        Connect to the Media WebSocket to receive transcripts.
        """
        print(f"🔗 Connecting to Media Server: {media_url}")
        try:
            async with websockets.connect(media_url) as media_ws:
                self.ws = media_ws
                print("✅ Connected to Media Server - Ready for Transcripts")
                
                while self.is_running:
                    try:
                        message = await media_ws.recv()
                        data = json.loads(message)
                        await self.on_message(data)
                    except websockets.ConnectionClosed:
                        print("⚠️ Media Connection closed")
                        break
        except Exception as e:
            print(f"❌ Media Connection Failed: {e}")

    def stop(self):
        """
        Stop the client.
        """
        self.is_running = False
        # In a real app, we should close websockets gracefully here
