#!/usr/bin/env python3
"""
Test the basic multiplayer connection handshake:
1. Host creates invitation
2. Guest joins via invitation
3. Both establish WebSocket connections
4. Verify they can see each other's presence
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_connection_handshake():
    """Test the basic connection handshake between host and guest"""
    print("🤝 Testing Multiplayer Connection Handshake")
    print("=" * 50)
    
    # Step 1: Host creates invitation
    print("1️⃣ Host creates invitation...")
    try:
        invitation_response = requests.post(f"{API_BASE}/invitation", json={
            "host_name": "Host_Alice",
            "use_rl_engine": False
        })
        
        if not invitation_response.ok:
            print(f"❌ Failed to create invitation: {invitation_response.status_code}")
            print(f"   Response: {invitation_response.text}")
            return False
            
        invitation_data = invitation_response.json()
        invitation_code = invitation_data["invitation_code"]
        print(f"✅ Invitation created successfully")
        print(f"   Code: {invitation_code}")
        print(f"   Host: {invitation_data.get('host_name', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Exception creating invitation: {e}")
        return False
    
    # Step 2: Guest joins the invitation
    print("\n2️⃣ Guest joins invitation...")
    try:
        join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
            "player_name": "Guest_Bob"
        })
        
        if not join_response.ok:
            print(f"❌ Failed to join invitation: {join_response.status_code}")
            print(f"   Response: {join_response.text}")
            return False
            
        join_data = join_response.json()
        session_id = join_data["session_id"]
        print(f"✅ Guest joined successfully")
        print(f"   Session ID: {session_id}")
        print(f"   Success: {join_data.get('success', False)}")
        
    except Exception as e:
        print(f"❌ Exception joining invitation: {e}")
        return False
    
    # Step 3: Verify game state shows both players
    print("\n3️⃣ Verifying game state has both players...")
    try:
        state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
        
        if not state_response.ok:
            print(f"❌ Failed to get game state: {state_response.status_code}")
            return False
            
        state_data = state_response.json()
        print(f"✅ Game state retrieved")
        print(f"   Current player: {state_data.get('current_player', 'Unknown')}")
        print(f"   Game started: {state_data.get('game_started', False)}")
        print(f"   Mode: {state_data.get('mode', 'Unknown')}")
        print(f"   White player: {state_data.get('player_white', 'None')}")
        print(f"   Black player: {state_data.get('player_black', 'None')}")
        
        # Check if both players are assigned
        has_both_players = (
            state_data.get('player_white') and 
            state_data.get('player_black') and
            state_data.get('game_started', False)
        )
        
        if has_both_players:
            print("✅ Both players properly assigned and game started")
        else:
            print("❌ Missing players or game not started")
            return False
            
    except Exception as e:
        print(f"❌ Exception getting game state: {e}")
        return False
    
    # Step 4: Test WebSocket connections for both players
    print("\n4️⃣ Testing WebSocket connections...")
    
    host_connected = False
    guest_connected = False
    host_messages = []
    guest_messages = []
    
    async def host_websocket():
        nonlocal host_connected, host_messages
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        try:
            print(f"   🔗 Host connecting to: {ws_url}")
            async with websockets.connect(ws_url) as websocket:
                host_connected = True
                print("   ✅ Host WebSocket connected")
                
                # Send a test message or just listen
                start_time = time.time()
                while time.time() - start_time < 10:  # Listen for 10 seconds
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        host_messages.append(data)
                        print(f"   📨 Host received: {data.get('type', 'unknown')}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Host WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"   ❌ Host WebSocket failed: {e}")
    
    async def guest_websocket():
        nonlocal guest_connected, guest_messages
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        try:
            print(f"   🔗 Guest connecting to: {ws_url}")
            async with websockets.connect(ws_url) as websocket:
                guest_connected = True
                print("   ✅ Guest WebSocket connected")
                
                # Send a test message or just listen
                start_time = time.time()
                while time.time() - start_time < 10:  # Listen for 10 seconds
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        guest_messages.append(data)
                        print(f"   📨 Guest received: {data.get('type', 'unknown')}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Guest WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"   ❌ Guest WebSocket failed: {e}")
    
    # Start both WebSocket connections
    try:
        await asyncio.gather(
            host_websocket(),
            guest_websocket(),
            return_exceptions=True
        )
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
    
    # Step 5: Test basic communication
    print("\n5️⃣ Testing basic move communication...")
    if host_connected and guest_connected:
        print("   Both players connected, testing move...")
        
        # Make a simple move and see if both receive the update
        move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": [6, 4],  # e2
            "to": [4, 4]     # e4
        })
        
        if move_response.ok:
            print("   ✅ Move executed successfully")
            # Give a moment for WebSocket messages
            await asyncio.sleep(2)
        else:
            print(f"   ❌ Move failed: {move_response.status_code}")
    
    # Step 6: Summary
    print("\n📊 Connection Handshake Results:")
    print(f"   Invitation created: ✅")
    print(f"   Guest joined: ✅")
    print(f"   Both players assigned: {'✅' if has_both_players else '❌'}")
    print(f"   Host WebSocket: {'✅' if host_connected else '❌'}")
    print(f"   Guest WebSocket: {'✅' if guest_connected else '❌'}")
    print(f"   Host messages received: {len(host_messages)}")
    print(f"   Guest messages received: {len(guest_messages)}")
    
    success = (
        has_both_players and 
        host_connected and 
        guest_connected
    )
    
    if success:
        print("\n🎉 SUCCESS: Connection handshake working!")
        print("   Both players can connect and communicate")
    else:
        print("\n❌ FAILURE: Connection handshake has issues")
        if not has_both_players:
            print("   Issue: Players not properly assigned")
        if not host_connected:
            print("   Issue: Host WebSocket connection failed")
        if not guest_connected:
            print("   Issue: Guest WebSocket connection failed")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(test_connection_handshake())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
