import asyncio
import httpx
import sys

async def check_server():
    url = "http://localhost:7870/gradio_api/mcp/sse"
    print(f"🔍 Testing connection to: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            print("   Sending GET request...")
            async with client.stream("GET", url, timeout=5.0) as response:
                print(f"   ✅ Connected! Status Code: {response.status_code}")
                print("   Headers:", dict(response.headers))
                
                print("   Waiting for events (reading first chunk)...")
                async for chunk in response.aiter_bytes():
                    print(f"   ✅ Received chunk: {chunk[:100]}...")
                    break
                print("   🎉 Stream seems alive!")
                return True
                
    except httpx.ConnectError:
        print("   ❌ Connection Refused: Is the server running on port 7870?")
        return False
    except httpx.ReadTimeout:
        print("   ❌ Read Timeout: Server accepted connection but sent no data.")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(check_server())
    except KeyboardInterrupt:
        pass
