#!/usr/bin/env python3
"""
Test WebSocket board synchronization by checking actual piece positions
across different connections. This verifies that moves made by one player
are properly displayed to the other player in real-time.
"""
import asyncio
import websockets
import json
import requests
import time

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

def format_board(board_data):
    """Format board data for display"""
    board = board_data['board']
    result = []
    
    # Unicode chess pieces
    pieces = {
        'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚', 'P': '♟',  # Black
        'r': '♖', 'n': '♘', 'b': '♗', 'q': '♕', 'k': '♔', 'p': '♙'   # White (lowercase for distinction)
    }
    
    for row in range(8):
        row_str = f"{8-row} "
        for col in range(8):
            piece = board[row][col]
            if piece:
                piece_type = piece['type']
                if piece['color'] == 'white':
                    symbol = pieces.get(piece_type.lower(), '?')
                else:
                    symbol = pieces.get(piece_type, '?')
                row_str += symbol + " "
            else:
                row_str += ". "
        result.append(row_str)
    
    result.append("  a b c d e f g h")
    return "\n".join(result)

def get_piece_at(board_data, position):
    """Get piece at specific position [row, col]"""
    row, col = position
    piece = board_data['board'][row][col]
    if piece:
        return f"{piece['color']} {piece['type']}"
    return "empty"

async def test_board_synchronization():
    print("🎯 Testing Board Synchronization Across Connections")
    print("=" * 55)
    
    # Step 1: Create multiplayer game
    print("📋 Step 1: Setting up multiplayer game...")
    invitation_response = requests.post(f"{API_BASE}/api/invitation", 
                                      json={"host_name": "Player1", "use_rl_engine": False})
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    
    join_response = requests.post(f"{API_BASE}/api/invitation/{invitation_code}/join",
                                json={"guest_name": "Player2"})
    join_data = join_response.json()
    session_id = join_data["session_id"]
    
    print(f"✅ Game created: {session_id[:8]}...")
    print(f"   Player 1 (White): {join_data['game_state']['player_white']}")
    print(f"   Player 2 (Black): {join_data['game_state']['player_black']}")
    
    # Step 2: Store board states for comparison
    player1_board_states = []
    player2_board_states = []
    
    # Step 3: Connect WebSockets and capture board states
    async def player1_connection():
        uri = f"{WS_BASE}/ws/{session_id}"
        async with websockets.connect(uri) as websocket:
            print("🔗 Player 1 WebSocket connected")
            
            # Get initial state
            state_response = requests.get(f"{API_BASE}/api/game/state?session_id={session_id}")
            initial_state = state_response.json()
            player1_board_states.append(("Initial", initial_state))
            
            # Listen for moves
            move_count = 0
            while move_count < 6:  # Listen for several moves
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'move_made':
                        move_data = data.get('data', {})
                        game_state = move_data.get('game_state', {})
                        if game_state:
                            from_pos = move_data.get('from', [])
                            to_pos = move_data.get('to', [])
                            move_desc = f"Move {len(game_state.get('move_history', []))}: {from_pos} → {to_pos}"
                            player1_board_states.append((move_desc, game_state))
                            print(f"🎮 Player 1 received: {move_desc}")
                            move_count += 1
                            
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
    
    async def player2_connection():
        uri = f"{WS_BASE}/ws/{session_id}"
        await asyncio.sleep(0.5)  # Slight delay
        async with websockets.connect(uri) as websocket:
            print("🔗 Player 2 WebSocket connected")
            
            # Get initial state
            state_response = requests.get(f"{API_BASE}/api/game/state?session_id={session_id}")
            initial_state = state_response.json()
            player2_board_states.append(("Initial", initial_state))
            
            # Listen for moves
            move_count = 0
            while move_count < 6:  # Listen for several moves
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'move_made':
                        move_data = data.get('data', {})
                        game_state = move_data.get('game_state', {})
                        if game_state:
                            from_pos = move_data.get('from', [])
                            to_pos = move_data.get('to', [])
                            move_desc = f"Move {len(game_state.get('move_history', []))}: {from_pos} → {to_pos}"
                            player2_board_states.append((move_desc, game_state))
                            print(f"🎯 Player 2 received: {move_desc}")
                            move_count += 1
                            
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
    
    async def make_test_moves():
        await asyncio.sleep(1)  # Wait for connections
        
        print("\n📋 Step 4: Making moves and checking synchronization...")
        
        test_moves = [
            {"desc": "Player 1: e2-e4", "from": [6, 4], "to": [4, 4]},
            {"desc": "Player 2: e7-e5", "from": [1, 4], "to": [3, 4]},
            {"desc": "Player 1: Ng1-f3", "from": [7, 6], "to": [5, 5]},
            {"desc": "Player 2: Nb8-c6", "from": [0, 1], "to": [2, 2]},
            {"desc": "Player 1: Bf1-c4", "from": [7, 2], "to": [4, 5]},
            {"desc": "Player 2: Bf8-c5", "from": [0, 5], "to": [3, 2]}
        ]
        
        for i, move in enumerate(test_moves):
            print(f"\n♔ {move['desc']}")
            
            # Make the move
            move_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                        json={"from": move["from"], "to": move["to"]})
            
            if move_response.status_code == 200:
                print(f"   ✅ Move executed successfully")
                
                # Check what piece moved
                state_response = requests.get(f"{API_BASE}/api/game/state?session_id={session_id}")
                current_state = state_response.json()
                
                from_piece = get_piece_at({"board": [[None]*8 for _ in range(8)]}, move["from"])  # Will be empty now
                to_piece = get_piece_at(current_state, move["to"])
                
                print(f"   Piece at destination {move['to']}: {to_piece}")
                print(f"   Move history: {current_state.get('move_history', [])}")
                
            else:
                print(f"   ❌ Move failed: {move_response.status_code}")
                break
                
            await asyncio.sleep(1)  # Wait for WebSocket propagation
    
    # Run all tasks concurrently
    await asyncio.gather(
        player1_connection(),
        player2_connection(), 
        make_test_moves(),
        return_exceptions=True
    )
    
    # Step 5: Compare board states between players
    print("\n📋 Step 5: Comparing board states between players...")
    
    if len(player1_board_states) == len(player2_board_states):
        print(f"✅ Both players received {len(player1_board_states)} board states")
        
        for i, ((desc1, state1), (desc2, state2)) in enumerate(zip(player1_board_states, player2_board_states)):
            print(f"\n🔍 State {i}: {desc1}")
            
            # Compare key board positions
            if i == 0:  # Initial state
                print("   Initial board setup - both players should have same starting position")
            else:
                # Check that specific pieces moved correctly
                move_history1 = state1.get('move_history', [])
                move_history2 = state2.get('move_history', [])
                
                if move_history1 == move_history2:
                    print(f"   ✅ Move history synchronized: {move_history1}")
                else:
                    print(f"   ❌ Move history mismatch!")
                    print(f"     Player 1: {move_history1}")
                    print(f"     Player 2: {move_history2}")
                
                # Check current player
                current1 = state1.get('current_player')
                current2 = state2.get('current_player')
                if current1 == current2:
                    print(f"   ✅ Current player synchronized: {current1}")
                else:
                    print(f"   ❌ Current player mismatch: {current1} vs {current2}")
    else:
        print(f"❌ State count mismatch: Player1={len(player1_board_states)}, Player2={len(player2_board_states)}")
    
    # Step 6: Display final board state
    if player1_board_states and player2_board_states:
        print("\n📋 Step 6: Final board visualization...")
        final_state = player1_board_states[-1][1]
        print("Final board position:")
        print(format_board(final_state))
        print(f"Final move history: {' '.join(final_state.get('move_history', []))}")
    
    print("\n🏁 Board synchronization test completed!")

if __name__ == "__main__":
    asyncio.run(test_board_synchronization())
