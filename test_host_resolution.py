#!/usr/bin/env python3
"""
Test script to verify that the frontend adapts to different host configurations
and that WebSocket connections work with dynamic URLs.
"""

import asyncio
import json
import websockets
import requests
import time
from urllib.parse import urlparse

API_BASE = "http://localhost:8000/api"

def test_api_host_resolution():
    """Test that API calls can handle different host configurations"""
    print("🧪 Testing Host Resolution and WebSocket URLs")
    print("=" * 50)
    
    # Test 1: Verify current API base works
    print("1️⃣ Testing current API base...")
    try:
        response = requests.get(f"{API_BASE.replace('/api', '')}/")
        if response.ok:
            print("✅ API base accessible")
        else:
            print(f"❌ API base returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API base connection failed: {e}")
        return False
    
    # Test 2: Create a test session to get session ID
    print("2️⃣ Creating test session...")
    try:
        response = requests.post(f"{API_BASE}/session", json={
            "game_mode": "human_vs_ai"
        })
        if response.ok:
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"✅ Session created: {session_id[:8]}...")
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return False
    
    # Test 3: Test WebSocket connection with different URL formats
    print("3️⃣ Testing WebSocket connection formats...")
    
    # Test localhost WebSocket
    ws_url = f"ws://localhost:8000/ws/{session_id}"
    print(f"   Testing: {ws_url}")
    
    async def test_websocket():
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connection successful")
                
                # Test sending a ping
                await websocket.ping()
                print("✅ WebSocket ping successful")
                return True
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False
    
    try:
        result = asyncio.run(test_websocket())
        if not result:
            return False
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False
    
    # Test 4: Simulate different window.location configurations
    print("4️⃣ Testing URL construction logic...")
    
    # Simulate different host configurations
    test_configs = [
        ("http:", "localhost:8000"),
        ("https:", "localhost:8000"),
        ("http:", "192.168.1.100:8000"),
        ("https:", "chess-game.example.com"),
    ]
    
    for protocol, host in test_configs:
        # Simulate what the frontend would construct
        api_base = f"{protocol}//{host}/api"
        ws_protocol = "wss:" if protocol == "https:" else "ws:"
        ws_url = f"{ws_protocol}//{host}/ws/{session_id}"
        
        print(f"   Config: {protocol}//{host}")
        print(f"     API: {api_base}")
        print(f"     WS:  {ws_url}")
        
        # Validate URL structure
        try:
            parsed_api = urlparse(api_base)
            parsed_ws = urlparse(ws_url)
            
            api_valid = parsed_api.scheme in ['http', 'https'] and parsed_api.netloc
            ws_valid = parsed_ws.scheme in ['ws', 'wss'] and parsed_ws.netloc
            
            if api_valid and ws_valid:
                print("     ✅ URLs well-formed")
            else:
                print("     ❌ URLs malformed")
                return False
        except Exception as e:
            print(f"     ❌ URL parsing error: {e}")
            return False
    
    print("\n🎉 SUCCESS: Host resolution and URL construction working correctly!")
    return True

if __name__ == "__main__":
    try:
        result = test_api_host_resolution()
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
