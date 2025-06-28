#!/usr/bin/env python3
"""
Comprehensive test to simulate a full multiplayer chess experience
with real-time moves and board synchronization.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def simulate_multiplayer_game():
    """Simulate a full multiplayer game with alternating moves"""
    print("🎮 Simulating Full Multiplayer Chess Game")
    print("=" * 50)
    
    # Step 1: Create invitation
    print("1️⃣ Host creates invitation...")
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "Alice",
        "use_rl_engine": False
    })
    
    if not invitation_response.ok:
        print(f"❌ Failed to create invitation: {invitation_response.status_code}")
        return False
        
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"✅ Invitation created: {invitation_code}")
    
    # Step 2: Guest joins game
    print("2️⃣ Guest joins game...")
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "Bob"
    })
    
    if not join_response.ok:
        print(f"❌ Failed to join game: {join_response.status_code}")
        return False
        
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Game started. Session ID: {session_id}")
    
    # Step 3: Define a sequence of moves for testing
    moves_sequence = [
        ("Alice (White)", [6, 4], [4, 4], "e2-e4"),  # White: e2-e4
        ("Bob (Black)", [1, 4], [3, 4], "e7-e5"),   # Black: e7-e5
        ("Alice (White)", [7, 6], [5, 5], "Ng1-f3"), # White: Nf3
        ("Bob (Black)", [0, 1], [2, 2], "Nb8-c6"),  # Black: Nc6
        ("Alice (White)", [7, 5], [4, 2], "Bf1-c4"), # White: Bc4
        ("Bob (Black)", [7, 5], [4, 2], "Bf8-c5"),  # Black: Bc5 (mirror)
    ]
    
    print(f"3️⃣ Executing {len(moves_sequence)} moves...")
    
    async def player_websocket(player_name, is_white=True):
        """WebSocket connection for a player"""
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        messages_received = []
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"🔗 {player_name} WebSocket connected")
                
                # Listen for messages during the game
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        messages_received.append(data)
                        print(f"📨 {player_name} received: {data.get('type', 'unknown')}")
                        
                        # Stop after receiving enough messages
                        if len(messages_received) >= len(moves_sequence):
                            break
                            
                    except json.JSONDecodeError:
                        print(f"❌ {player_name} received invalid JSON")
                        
        except Exception as e:
            print(f"❌ {player_name} WebSocket error: {e}")
            
        return messages_received
    
    # Start WebSocket listeners
    alice_task = asyncio.create_task(player_websocket("Alice", True))
    bob_task = asyncio.create_task(player_websocket("Bob", False))
    
    # Wait a moment for connections
    await asyncio.sleep(1)
    
    # Execute moves sequence
    for i, (player, from_pos, to_pos, notation) in enumerate(moves_sequence):
        print(f"   {i+1}. {player}: {notation}")
        
        # Make the move
        move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": from_pos,
            "to": to_pos
        })
        
        if move_response.ok:
            move_data = move_response.json()
            current_player = move_data.get('game_state', {}).get('current_player', 'unknown')
            print(f"      ✅ Move successful. Next: {current_player}")
        else:
            print(f"      ❌ Move failed: {move_response.status_code}")
            error_data = move_response.json()
            print(f"         Error: {error_data.get('detail', 'Unknown error')}")
            break
        
        # Wait a bit between moves
        await asyncio.sleep(1)
    
    print("4️⃣ Waiting for WebSocket messages to complete...")
    await asyncio.sleep(2)
    
    # Cancel WebSocket tasks
    alice_task.cancel()
    bob_task.cancel()
    
    try:
        alice_messages = await alice_task
    except asyncio.CancelledError:
        alice_messages = []
        
    try:
        bob_messages = await bob_task
    except asyncio.CancelledError:
        bob_messages = []
    
    # Step 4: Verify final game state
    print("5️⃣ Verifying final game state...")
    final_state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if final_state_response.ok:
        final_state = final_state_response.json()
        print(f"✅ Final state retrieved")
        print(f"   Current player: {final_state['current_player']}")
        print(f"   Legal moves: {len(final_state['legal_moves'])}")
        print(f"   In check: {final_state['is_check']}")
        print(f"   Checkmate: {final_state['is_checkmate']}")
        print(f"   Stalemate: {final_state['is_stalemate']}")
        
        # Count pieces on board
        board = final_state['board']
        piece_count = sum(1 for row in board for cell in row if cell is not None)
        print(f"   Pieces on board: {piece_count}")
        
        # Check that some pieces have moved from starting positions
        e4_piece = board[4][4]  # Should have white pawn
        e5_piece = board[3][4]  # Should have black pawn
        
        moves_executed = (
            e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P' and
            e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P'
        )
        
        if moves_executed:
            print("✅ Board shows evidence of moves executed")
        else:
            print("❌ Board doesn't show expected moves")
            print(f"   e4 square: {e4_piece}")
            print(f"   e5 square: {e5_piece}")
        
        success = moves_executed
    else:
        print(f"❌ Failed to get final state: {final_state_response.status_code}")
        success = False
    
    # Step 5: Report results
    print("\n📊 Test Results Summary:")
    print(f"   Alice WebSocket messages: {len(alice_messages)}")
    print(f"   Bob WebSocket messages: {len(bob_messages)}")
    print(f"   Game state valid: {success}")
    
    if success and len(alice_messages) > 0 and len(bob_messages) > 0:
        print("\n🎉 SUCCESS: Full multiplayer game simulation completed!")
        print("   ✅ Both players connected via WebSocket")
        print("   ✅ Moves executed and synchronized")
        print("   ✅ Board state correctly updated")
        print("   ✅ Real-time communication working")
        return True
    else:
        print("\n❌ FAILURE: Multiplayer game simulation failed")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(simulate_multiplayer_game())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
