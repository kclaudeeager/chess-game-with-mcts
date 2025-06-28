#!/usr/bin/env python3
"""
Simple test to verify core multiplayer functionality: 
both players can move and see moves in real-time.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_basic_multiplayer():
    """Test basic multiplayer: white move, black move, both via WebSocket"""
    print("🎯 Testing Basic Multiplayer Functionality")
    print("=" * 45)
    
    # Create game
    print("1️⃣ Setting up multiplayer game...")
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "TestWhite",
        "use_rl_engine": False
    })
    
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "TestBlack"
    })
    
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Game ready. Session: {session_id[:8]}...")
    
    # Test simple move sequence
    print("2️⃣ Testing move sequence...")
    
    # White's first move: e2-e4
    print("   White plays e2-e4...")
    white_move = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
        "from": [6, 4], "to": [4, 4]
    })
    
    if white_move.ok:
        state_after_white = white_move.json()
        current_player = state_after_white.get('game_state', {}).get('current_player', 'unknown')
        print(f"   ✅ White move successful. Current player: {current_player}")
        
        if current_player == 'black':
            print("   Black can now move...")
            
            # Black's response: e7-e5
            print("   Black plays e7-e5...")
            black_move = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                "from": [1, 4], "to": [3, 4]
            })
            
            if black_move.ok:
                state_after_black = black_move.json()
                current_player = state_after_black.get('game_state', {}).get('current_player', 'unknown')
                print(f"   ✅ Black move successful. Current player: {current_player}")
                
                # Verify board state
                board = state_after_black.get('game_state', {}).get('board', [])
                if board:
                    e4_piece = board[4][4]
                    e5_piece = board[3][4]
                    
                    e4_ok = e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P'
                    e5_ok = e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P'
                    
                    if e4_ok and e5_ok:
                        print("   ✅ Board state correct: both moves visible")
                        success = True
                    else:
                        print(f"   ❌ Board state incorrect: e4={e4_piece}, e5={e5_piece}")
                        success = False
                else:
                    print("   ❌ No board data in response")
                    success = False
            else:
                print(f"   ❌ Black move failed: {black_move.status_code}")
                success = False
        else:
            print(f"   ❌ Wrong current player after white move: {current_player}")
            success = False
    else:
        print(f"   ❌ White move failed: {white_move.status_code}")
        success = False
    
    # Test WebSocket real-time updates
    print("3️⃣ Testing WebSocket real-time updates...")
    
    async def test_websocket_updates():
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   🔗 WebSocket connected")
                
                # Make another move and see if we get notified
                move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                    "from": [7, 6], "to": [5, 5]  # White: Ng1-f3
                })
                
                if move_response.ok:
                    print("   📤 Move sent, waiting for WebSocket notification...")
                    
                    # Wait for WebSocket message
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        data = json.loads(message)
                        print(f"   📨 Received: {data.get('type', 'unknown')}")
                        return True
                    except asyncio.TimeoutError:
                        print("   ⏰ No WebSocket message received")
                        return False
                else:
                    print("   ❌ Test move failed")
                    return False
                    
        except Exception as e:
            print(f"   ❌ WebSocket error: {e}")
            return False
    
    websocket_ok = await test_websocket_updates()
    
    # Final result
    print("\n📊 Results:")
    print(f"   Move alternation: {'✅' if success else '❌'}")
    print(f"   Board synchronization: {'✅' if success else '❌'}")
    print(f"   WebSocket updates: {'✅' if websocket_ok else '❌'}")
    
    overall_success = success and websocket_ok
    print(f"\n{'🎉 SUCCESS' if overall_success else '❌ FAILURE'}: Basic multiplayer functionality {'working' if overall_success else 'has issues'}")
    
    return overall_success

if __name__ == "__main__":
    try:
        result = asyncio.run(test_basic_multiplayer())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
