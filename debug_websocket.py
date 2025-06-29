#!/usr/bin/env python3
"""
Debug test to check WebSocket connectivity and message flow
"""
import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def debug_websocket_flow():
    print("🔍 Debugging WebSocket Multiplayer Flow")
    print("=" * 50)
    
    # Step 1: Create invitation
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "Alice",
        "use_rl_engine": False
    })
    
    if not invitation_response.ok:
        print(f"❌ Failed to create invitation: {invitation_response.status_code}")
        return
    
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"✅ Created invitation: {invitation_code}")
    
    # Step 2: Join game
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "Bob"
    })
    
    if not join_response.ok:
        print(f"❌ Failed to join game: {join_response.status_code}")
        print(join_response.text)
        return
    
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Bob joined session: {session_id}")
    
    # Check session state
    state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if state_response.ok:
        state_data = state_response.json()
        print(f"📋 Game state: White={state_data.get('player_white')}, Black={state_data.get('player_black')}")
        print(f"📋 Current player: {state_data.get('current_player')}")
        print(f"📋 Game started: {state_data.get('game_started')}")
    
    # Step 3: Test WebSocket connections
    ws_url = f"ws://localhost:8000/ws/{session_id}"
    print(f"🔗 Testing WebSocket connections to: {ws_url}")
    
    alice_messages = []
    bob_messages = []
    
    async def alice_ws():
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   🟢 Alice WebSocket connected")
                
                # Listen for 10 seconds
                end_time = time.time() + 10
                while time.time() < end_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        alice_messages.append(data)
                        print(f"   📨 Alice received: {data.get('type', 'unknown')}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ❌ Alice WebSocket error: {e}")
                        break
        except Exception as e:
            print(f"   ❌ Alice WebSocket connection failed: {e}")
    
    async def bob_ws():
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   🟢 Bob WebSocket connected")
                
                # Listen for 10 seconds
                end_time = time.time() + 10
                while time.time() < end_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        bob_messages.append(data)
                        print(f"   📨 Bob received: {data.get('type', 'unknown')}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ❌ Bob WebSocket error: {e}")
                        break
        except Exception as e:
            print(f"   ❌ Bob WebSocket connection failed: {e}")
    
    async def test_moves():
        # Wait for connections
        await asyncio.sleep(2)
        
        print("\n🎯 Testing move with WebSocket broadcast...")
        
        # Alice makes first move
        print("   Alice (White) making move e2-e4...")
        move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": [6, 4],
            "to": [4, 4],
            "player_name": "Alice"
        })
        
        if move_response.ok:
            print("   ✅ Move API call successful")
            move_data = move_response.json()
            print(f"   📋 Next player: {move_data.get('game_state', {}).get('current_player', 'unknown')}")
        else:
            print(f"   ❌ Move failed: {move_response.status_code}")
            print(f"   Error: {move_response.text}")
        
        # Wait for WebSocket messages
        await asyncio.sleep(3)
        
        print(f"\n📊 Message Summary:")
        print(f"   Alice received {len(alice_messages)} messages")
        print(f"   Bob received {len(bob_messages)} messages")
        
        if alice_messages:
            print("   Alice messages:")
            for msg in alice_messages:
                print(f"     - {msg.get('type', 'unknown')}: {msg}")
        
        if bob_messages:
            print("   Bob messages:")
            for msg in bob_messages:
                print(f"     - {msg.get('type', 'unknown')}: {msg}")
    
    # Run all tasks concurrently
    await asyncio.gather(
        alice_ws(),
        bob_ws(),
        test_moves(),
        return_exceptions=True
    )

if __name__ == "__main__":
    asyncio.run(debug_websocket_flow())
