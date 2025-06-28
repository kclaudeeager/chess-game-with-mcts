#!/usr/bin/env python3
"""
Test script to verify that both white and black players can move in multiplayer mode
and that board state is synchronized correctly.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_multiplayer_movement():
    """Test that both players can move and board updates correctly"""
    print("🧪 Testing Multiplayer Player Movement")
    print("=" * 50)
    
    # Step 1: Create invitation
    print("1️⃣ Creating invitation...")
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "TestWhite",
        "use_rl_engine": False
    })
    
    if not invitation_response.ok:
        print(f"❌ Failed to create invitation: {invitation_response.status_code}")
        return False
        
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"✅ Invitation created: {invitation_code}")
    
    # Step 2: Join game as black
    print("2️⃣ Joining game as black...")
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "TestBlack"
    })
    
    if not join_response.ok:
        print(f"❌ Failed to join game: {join_response.status_code}")
        return False
        
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Joined game. Session ID: {session_id}")
    
    # Step 3: Get initial board state
    print("3️⃣ Checking initial game state...")
    state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if not state_response.ok:
        print(f"❌ Failed to get game state: {state_response.status_code}")
        return False
        
    initial_state = state_response.json()
    print(f"✅ Initial state - Current player: {initial_state['current_player']}")
    print(f"   Legal moves: {len(initial_state['legal_moves'])}")
    
    # Step 4: Test WebSocket connections for both players
    print("4️⃣ Testing WebSocket connections...")
    
    # Connect as both players
    white_ws_url = f"ws://localhost:8000/ws/{session_id}"
    black_ws_url = f"ws://localhost:8000/ws/{session_id}"
    
    async def white_player():
        async with websockets.connect(white_ws_url) as websocket:
            print("🔗 White player WebSocket connected")
            
            # Make first move as white (e2-e4)
            move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                "from": [6, 4],  # e2
                "to": [4, 4]     # e4
            })
            
            if move_response.ok:
                print("♟️ White made move: e2-e4")
            else:
                print(f"❌ White move failed: {move_response.status_code}")
                return False
            
            # Wait for WebSocket message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"📨 White received WebSocket: {data.get('type', 'unknown')}")
                return True
            except asyncio.TimeoutError:
                print("⏰ White WebSocket timeout")
                return False
    
    async def black_player():
        async with websockets.connect(black_ws_url) as websocket:
            print("🔗 Black player WebSocket connected")
            
            # Wait a bit for white's move
            await asyncio.sleep(2)
            
            # Check if it's black's turn
            state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
            if state_response.ok:
                current_state = state_response.json()
                print(f"🔍 After white's move - Current player: {current_state['current_player']}")
                
                if current_state['current_player'] == 'black':
                    # Make move as black (e7-e5)
                    move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                        "from": [1, 4],  # e7
                        "to": [3, 4]     # e5
                    })
                    
                    if move_response.ok:
                        print("♟️ Black made move: e7-e5")
                    else:
                        print(f"❌ Black move failed: {move_response.status_code}")
                        return False
                else:
                    print(f"⚠️ Not black's turn after white's move. Current: {current_state['current_player']}")
                    return False
            
            # Wait for WebSocket message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"📨 Black received WebSocket: {data.get('type', 'unknown')}")
                return True
            except asyncio.TimeoutError:
                print("⏰ Black WebSocket timeout")
                return False
    
    # Run both players concurrently
    try:
        white_result, black_result = await asyncio.gather(
            white_player(),
            black_player(),
            return_exceptions=True
        )
        
        if isinstance(white_result, Exception):
            print(f"❌ White player error: {white_result}")
            white_result = False
            
        if isinstance(black_result, Exception):
            print(f"❌ Black player error: {black_result}")
            black_result = False
            
    except Exception as e:
        print(f"❌ Concurrent execution error: {e}")
        return False
    
    # Step 5: Verify final board state
    print("5️⃣ Verifying final board state...")
    final_state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if final_state_response.ok:
        final_state = final_state_response.json()
        print(f"✅ Final state - Current player: {final_state['current_player']}")
        print(f"   Legal moves: {len(final_state['legal_moves'])}")
        
        # Check that pieces have moved
        board = final_state['board']
        e4_piece = board[4][4]  # Should have white pawn
        e5_piece = board[3][4]  # Should have black pawn
        
        e4_correct = e4_piece and e4_piece['color'] == 'white' and e4_piece['type'] == 'P'
        e5_correct = e5_piece and e5_piece['color'] == 'black' and e5_piece['type'] == 'P'
        
        if e4_correct and e5_correct:
            print("✅ Board state correctly updated - both moves executed")
            success = True
        else:
            print("❌ Board state incorrect:")
            print(f"   e4 piece: {e4_piece} (expected white pawn)")
            print(f"   e5 piece: {e5_piece} (expected black pawn)")
            success = False
    else:
        print(f"❌ Failed to get final state: {final_state_response.status_code}")
        success = False
    
    # Overall result
    if white_result and black_result and success:
        print("\n🎉 SUCCESS: Both players can move and board updates correctly!")
        return True
    else:
        print(f"\n❌ FAILURE: white_ok={white_result}, black_ok={black_result}, board_ok={success}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_multiplayer_movement())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
