#!/usr/bin/env python3
"""
Integration test to verify the complete frontend-backend multiplayer flow.
This simulates the exact flow a user would experience in the browser.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_frontend_multiplayer_flow():
    """Test the complete frontend multiplayer user flow"""
    print("🌐 Testing Frontend Multiplayer Integration")
    print("=" * 50)
    
    # Step 1: Host creates invitation (like clicking "Set Name" in frontend)
    print("1️⃣ Host creates invitation (frontend: setting player name)...")
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "Alice",
        "use_rl_engine": False
    })
    
    if not invitation_response.ok:
        print(f"❌ Failed to create invitation: {invitation_response.status_code}")
        return False
    
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"✅ Host 'Alice' created invitation: {invitation_code}")
    
    # Generate invitation URL (what frontend would show)
    invitation_url = f"http://localhost:8000?invitation_code={invitation_code}"
    print(f"   Invitation URL: {invitation_url}")
    
    # Step 2: Guest receives invitation and gets invitation details
    print("\n2️⃣ Guest accesses invitation URL (frontend: loading join page)...")
    invitation_details_response = requests.get(f"{API_BASE}/invitation/{invitation_code}")
    
    if not invitation_details_response.ok:
        print(f"❌ Failed to get invitation details: {invitation_details_response.status_code}")
        return False
    
    invitation_details = invitation_details_response.json()
    print(f"✅ Guest sees invitation from: {invitation_details.get('host_name', 'Unknown')}")
    
    # Step 3: Guest joins the game (like clicking "Join Game" in frontend)
    print("\n3️⃣ Guest joins game (frontend: submitting join form)...")
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "Bob"
    })
    
    if not join_response.ok:
        print(f"❌ Failed to join game: {join_response.status_code}")
        return False
    
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Guest 'Bob' joined successfully. Session: {session_id}")
    
    # Step 4: Both players establish WebSocket connections (frontend: connectWebSocket())
    print("\n4️⃣ Both players establish WebSocket connections...")
    
    host_connected = False
    guest_connected = False
    host_move_count = 0
    guest_move_count = 0
    
    async def alice_frontend():
        """Simulate Alice's frontend WebSocket connection"""
        nonlocal host_connected, host_move_count
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                host_connected = True
                print("   🔗 Alice (Host) WebSocket connected")
                
                # Listen for 15 seconds
                start_time = time.time()
                while time.time() - start_time < 15:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        if data.get('type') == 'move_made':
                            host_move_count += 1
                            print(f"   📨 Alice received move notification #{host_move_count}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Alice WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"   ❌ Alice WebSocket failed: {e}")
    
    async def bob_frontend():
        """Simulate Bob's frontend WebSocket connection"""
        nonlocal guest_connected, guest_move_count
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                guest_connected = True
                print("   🔗 Bob (Guest) WebSocket connected")
                
                # Listen for 15 seconds
                start_time = time.time()
                while time.time() - start_time < 15:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        if data.get('type') == 'move_made':
                            guest_move_count += 1
                            print(f"   📨 Bob received move notification #{guest_move_count}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Bob WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"   ❌ Bob WebSocket failed: {e}")
    
    async def simulate_gameplay():
        """Simulate alternating moves between players"""
        # Wait for connections
        await asyncio.sleep(2)
        
        if not (host_connected and guest_connected):
            print("   ❌ WebSocket connections not established")
            return
        
        print("\n5️⃣ Simulating alternating gameplay...")
        
        # Move sequence with detailed frontend simulation
        moves = [
            ("Alice (White)", [6, 4], [4, 4], "e2-e4"),
            ("Bob (Black)", [1, 4], [3, 4], "e7-e5"),
            ("Alice (White)", [7, 6], [5, 5], "Ng1-f3"),
            ("Bob (Black)", [0, 1], [2, 2], "Nb8-c6"),
        ]
        
        for i, (player, from_pos, to_pos, notation) in enumerate(moves):
            print(f"   {i+1}. {player} clicks on board to play {notation}")
            
            # Get current game state (frontend would do this)
            state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
            if state_response.ok:
                state_data = state_response.json()
                current_player = state_data.get('current_player', 'unknown')
                legal_moves = len(state_data.get('legal_moves', []))
                print(f"      Game state: {current_player} to move, {legal_moves} legal moves")
            
            # Make the move (frontend: makeMove function)
            move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                "from": from_pos,
                "to": to_pos
            })
            
            if move_response.ok:
                move_data = move_response.json()
                next_player = move_data.get('game_state', {}).get('current_player', 'unknown')
                print(f"      ✅ Move successful. Next player: {next_player}")
                
                # Wait for WebSocket notifications (frontend: handleWebSocketMessage)
                await asyncio.sleep(1.5)
            else:
                print(f"      ❌ Move failed: {move_response.status_code}")
                error_data = move_response.json()
                print(f"         Error: {error_data.get('detail', 'Unknown')}")
                break
        
        # Final state check
        print("\n6️⃣ Verifying final game state...")
        final_state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
        if final_state_response.ok:
            final_state = final_state_response.json()
            board = final_state['board']
            current_player = final_state.get('current_player', 'unknown')
            legal_moves = len(final_state.get('legal_moves', []))
            
            print(f"   Current player: {current_player}")
            print(f"   Legal moves: {legal_moves}")
            
            # Check that key pieces moved
            e4_piece = board[4][4]
            e5_piece = board[3][4]
            f3_piece = board[5][5]
            c6_piece = board[2][2]
            
            moves_ok = (
                e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P' and
                e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P' and
                f3_piece and f3_piece.get('color') == 'white' and f3_piece.get('type') == 'N' and
                c6_piece and c6_piece.get('color') == 'black' and c6_piece.get('type') == 'N'
            )
            
            if moves_ok:
                print("   ✅ All moves executed correctly on board")
            else:
                print("   ❌ Board state doesn't match expected moves")
                print(f"      e4: {e4_piece}, e5: {e5_piece}")
                print(f"      f3: {f3_piece}, c6: {c6_piece}")
            
            return moves_ok
        else:
            print(f"   ❌ Failed to get final state: {final_state_response.status_code}")
            return False
    
    # Run all frontend simulations concurrently
    results = await asyncio.gather(
        alice_frontend(),
        bob_frontend(),
        simulate_gameplay(),
        return_exceptions=True
    )
    
    # Check for exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"   ❌ Task {i} failed with exception: {result}")
    
    gameplay_success = results[2] if not isinstance(results[2], Exception) else False
    
    # Step 7: Results summary
    print("\n📊 Frontend Integration Test Results:")
    print(f"   Invitation creation: ✅")
    print(f"   Invitation details retrieval: ✅")
    print(f"   Guest join process: ✅")
    print(f"   Alice WebSocket connection: {'✅' if host_connected else '❌'}")
    print(f"   Bob WebSocket connection: {'✅' if guest_connected else '❌'}")
    print(f"   Alice move notifications: {host_move_count}")
    print(f"   Bob move notifications: {guest_move_count}")
    print(f"   Gameplay simulation: {'✅' if gameplay_success else '❌'}")
    
    overall_success = (
        host_connected and 
        guest_connected and 
        host_move_count > 0 and 
        guest_move_count > 0 and 
        gameplay_success
    )
    
    if overall_success:
        print("\n🎉 SUCCESS: Complete frontend-backend integration working!")
        print("   ✅ Invitation system works end-to-end")
        print("   ✅ WebSocket real-time communication works")
        print("   ✅ Move synchronization works perfectly")
        print("   ✅ Both players can see each other's moves instantly")
        print("\n🚀 Ready for real users to play multiplayer chess!")
    else:
        print("\n❌ FAILURE: Integration issues detected")
        if not host_connected or not guest_connected:
            print("   Issue: WebSocket connections failed")
        if host_move_count == 0 or guest_move_count == 0:
            print("   Issue: Move notifications not working")
        if not gameplay_success:
            print("   Issue: Gameplay simulation failed")
    
    return overall_success

if __name__ == "__main__":
    try:
        result = asyncio.run(test_frontend_multiplayer_flow())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
