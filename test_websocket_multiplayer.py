#!/usr/bin/env python3
"""
Test script for multiplayer WebSocket real-time synchronization.
This simulates two players connecting to the same game session.
"""
import asyncio
import websockets
import json
import requests
import time

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

async def test_multiplayer_websockets():
    print("🎮 Testing Multiplayer WebSocket Synchronization")
    print("=" * 50)
    
    # Step 1: Create invitation
    print("📋 Step 1: Creating invitation...")
    invitation_response = requests.post(f"{API_BASE}/api/invitation", 
                                      json={"host_name": "TestPlayer1", "use_rl_engine": False})
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"✅ Created invitation: {invitation_code}")
    
    # Step 2: Join the game
    print("📋 Step 2: Joining game...")
    join_response = requests.post(f"{API_BASE}/api/invitation/{invitation_code}/join",
                                json={"guest_name": "TestPlayer2"})
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Joined game, session ID: {session_id[:8]}...")
    
    # Step 3: Connect WebSockets for both players
    print("📋 Step 3: Connecting WebSockets...")
    
    async def player1_websocket():
        uri = f"{WS_BASE}/ws/{session_id}"
        print(f"🔗 Player 1 connecting to: {uri}")
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Player 1 WebSocket connected")
                
                # Listen for messages with timeout
                for i in range(10):  # Listen for 10 messages max
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        print(f"🎮 Player 1 received: {data.get('type', 'unknown')}")
                        if data.get('type') == 'move_made':
                            move_data = data.get('data', {})
                            print(f"   Move: {move_data.get('from')} → {move_data.get('to')}")
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
        except Exception as e:
            print(f"❌ Player 1 WebSocket error: {e}")
    
    async def player2_websocket():
        uri = f"{WS_BASE}/ws/{session_id}"
        print(f"🔗 Player 2 connecting to: {uri}")
        await asyncio.sleep(1)  # Slight delay
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Player 2 WebSocket connected")
                
                # Listen for messages with timeout
                for i in range(10):  # Listen for 10 messages max
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        print(f"🎯 Player 2 received: {data.get('type', 'unknown')}")
                        if data.get('type') == 'move_made':
                            move_data = data.get('data', {})
                            print(f"   Move: {move_data.get('from')} → {move_data.get('to')}")
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
        except Exception as e:
            print(f"❌ Player 2 WebSocket error: {e}")
    
    async def make_test_moves():
        await asyncio.sleep(2)  # Wait for connections
        
        print("📋 Step 4: Making test moves...")
        
        # Player 1 (White) moves e2-e4
        print("♔ Player 1 making move: e2-e4")
        move1_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                     json={"from": [6, 4], "to": [4, 4]})
        if move1_response.status_code == 200:
            print("✅ Move 1 successful")
        else:
            print(f"❌ Move 1 failed: {move1_response.status_code}")
        
        await asyncio.sleep(2)
        
        # Player 2 (Black) moves e7-e5
        print("♛ Player 2 making move: e7-e5")
        move2_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                     json={"from": [1, 4], "to": [3, 4]})
        if move2_response.status_code == 200:
            print("✅ Move 2 successful")
        else:
            print(f"❌ Move 2 failed: {move2_response.status_code}")
        
        await asyncio.sleep(2)
        
        # Player 1 (White) moves Ng1-f3
        print("♔ Player 1 making move: Ng1-f3")
        move3_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                     json={"from": [7, 6], "to": [5, 5]})
        if move3_response.status_code == 200:
            print("✅ Move 3 successful")
        else:
            print(f"❌ Move 3 failed: {move3_response.status_code}")
        
        await asyncio.sleep(3)
        print("📋 Test completed!")
    
    # Run WebSocket connections and move making concurrently with timeout
    try:
        await asyncio.wait_for(
            asyncio.gather(
                player1_websocket(),
                player2_websocket(),
                make_test_moves(),
                return_exceptions=True
            ),
            timeout=20.0  # 20 second timeout for entire test
        )
    except asyncio.TimeoutError:
        print("⏰ Test completed (timeout reached)")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("🏁 WebSocket multiplayer test finished!")

if __name__ == "__main__":
    asyncio.run(test_multiplayer_websockets())
