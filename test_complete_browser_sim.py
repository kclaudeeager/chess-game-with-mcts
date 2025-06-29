#!/usr/bin/env python3
"""
Complete browser simulation test - tests the exact flow a user would experience
"""
import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_complete_browser_simulation():
    print("🌐 Complete Browser Simulation Test")
    print("=" * 50)
    
    # === ALICE'S BROWSER SIMULATION ===
    print("\n👩 Alice opens her browser and navigates to chess game...")
    
    # Alice sets her name (frontend: setPlayerName function)
    print("1. Alice enters name 'Alice' and clicks 'Set Name'")
    alice_invite_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "Alice",
        "use_rl_engine": False
    })
    
    if not alice_invite_response.ok:
        print(f"❌ Alice's invitation creation failed: {alice_invite_response.status_code}")
        return False
    
    alice_data = alice_invite_response.json()
    invitation_code = alice_data["invitation_code"]
    invitation_url = f"http://localhost:8000?invitation_code={invitation_code}"
    
    print(f"   ✅ Alice gets invitation code: {invitation_code}")
    print(f"   📋 Alice copies invitation URL: {invitation_url}")
    
    # === BOB'S BROWSER SIMULATION ===
    print("\n👨 Bob receives invitation URL and opens it in his browser...")
    
    # Bob clicks invitation URL (frontend: showJoinGameInterface)
    print("2. Bob clicks invitation URL and sees join page")
    bob_invite_details = requests.get(f"{API_BASE}/invitation/{invitation_code}")
    
    if not bob_invite_details.ok:
        print(f"❌ Bob can't load invitation: {bob_invite_details.status_code}")
        return False
    
    bob_details = bob_invite_details.json()
    print(f"   ✅ Bob sees invitation from: {bob_details.get('host_name', 'Unknown')}")
    
    # Bob enters name and joins (frontend: joinGameSession)
    print("3. Bob enters name 'Bob' and clicks 'Join Game'")
    bob_join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "Bob"
    })
    
    if not bob_join_response.ok:
        print(f"❌ Bob can't join game: {bob_join_response.status_code}")
        return False
    
    bob_join_data = bob_join_response.json()
    session_id = bob_join_data["session_id"]
    print(f"   ✅ Bob joined successfully! Session: {session_id}")
    
    # === WEBSOCKET CONNECTIONS (frontend: connectWebSocket) ===
    print("\n🔗 Both browsers establish WebSocket connections...")
    
    alice_connected = False
    bob_connected = False
    alice_moves_received = 0
    bob_moves_received = 0
    
    async def alice_browser():
        nonlocal alice_connected, alice_moves_received
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                alice_connected = True
                print("   🟢 Alice's browser WebSocket connected")
                
                # Listen for WebSocket messages (frontend: handleWebSocketMessage)
                start_time = time.time()
                while time.time() - start_time < 12:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        if data.get('type') == 'move_made':
                            alice_moves_received += 1
                            print(f"   📨 Alice's browser received move #{alice_moves_received}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Alice WebSocket error: {e}")
                        break
        except Exception as e:
            print(f"   ❌ Alice WebSocket failed: {e}")
    
    async def bob_browser():
        nonlocal bob_connected, bob_moves_received
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                bob_connected = True
                print("   🟢 Bob's browser WebSocket connected")
                
                # Listen for WebSocket messages (frontend: handleWebSocketMessage)
                start_time = time.time()
                while time.time() - start_time < 12:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        if data.get('type') == 'move_made':
                            bob_moves_received += 1
                            print(f"   📨 Bob's browser received move #{bob_moves_received}")
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ Bob WebSocket error: {e}")
                        break
        except Exception as e:
            print(f"   ❌ Bob WebSocket failed: {e}")
    
    async def simulate_gameplay():
        # Wait for connections
        await asyncio.sleep(2)
        
        if not (alice_connected and bob_connected):
            print("   ❌ Browser connections not established")
            return False
        
        print("\n🎮 Simulating actual gameplay...")
        
        # === ALICE'S TURN ===
        print("\n🔴 Alice's turn (White pieces)")
        print("4. Alice clicks on e2 pawn, sees legal moves highlighted")
        print("5. Alice clicks on e4 to make move e2-e4")
        
        # Alice makes move (frontend: handleSquareClick -> makeMove)
        alice_move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": [6, 4],  # e2
            "to": [4, 4],    # e4
            "player_name": "Alice"
        })
        
        if alice_move_response.ok:
            print("   ✅ Alice's move successful (e2-e4)")
            # Wait for WebSocket propagation
            await asyncio.sleep(1.5)
        else:
            print(f"   ❌ Alice's move failed: {alice_move_response.status_code}")
            error_data = alice_move_response.json()
            print(f"   Error: {error_data.get('detail', 'Unknown')}")
            return False
        
        # === BOB'S TURN ===
        print("\n🔵 Bob's turn (Black pieces)")
        print("6. Bob clicks on e7 pawn, sees legal moves highlighted")  
        print("7. Bob clicks on e5 to make move e7-e5")
        
        # Bob makes move (frontend: handleSquareClick -> makeMove)
        bob_move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": [1, 4],  # e7
            "to": [3, 4],    # e5
            "player_name": "Bob"
        })
        
        if bob_move_response.ok:
            print("   ✅ Bob's move successful (e7-e5)")
            # Wait for WebSocket propagation
            await asyncio.sleep(1.5)
        else:
            print(f"   ❌ Bob's move failed: {bob_move_response.status_code}")
            error_data = bob_move_response.json()
            print(f"   Error: {error_data.get('detail', 'Unknown')}")
            return False
        
        # === TURN ENFORCEMENT TEST ===
        print("\n🔒 Testing turn enforcement...")
        print("8. Bob tries to move again (should be rejected - not his turn)")
        
        bob_invalid_move = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
            "from": [1, 3],  # d7
            "to": [3, 3],    # d5
            "player_name": "Bob"
        })
        
        if bob_invalid_move.ok:
            print("   ❌ ERROR: Bob was allowed to move twice!")
            return False
        else:
            print("   ✅ Bob's second move correctly rejected (turn enforcement working)")
        
        # Final verification
        await asyncio.sleep(2)
        
        # Check final board state
        final_state = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
        if final_state.ok:
            final_data = final_state.json()
            board = final_data['board']
            
            # Check if moves are reflected
            e4_piece = board[4][4]  # Should have white pawn
            e5_piece = board[3][4]  # Should have black pawn
            
            moves_correct = (
                e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P' and
                e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P'
            )
            
            if moves_correct:
                print("   ✅ Board state correct: both moves reflected")
            else:
                print(f"   ❌ Board state incorrect. e4: {e4_piece}, e5: {e5_piece}")
                return False
        
        return True
    
    # Run all browser simulations concurrently
    results = await asyncio.gather(
        alice_browser(),
        bob_browser(), 
        simulate_gameplay(),
        return_exceptions=True
    )
    
    gameplay_success = results[2] if not isinstance(results[2], Exception) else False
    
    # === FINAL RESULTS ===
    print("\n📊 Complete Browser Simulation Results:")
    print(f"   Alice invitation creation: ✅")
    print(f"   Bob invitation loading: ✅")
    print(f"   Bob game joining: ✅")
    print(f"   Alice WebSocket connection: {'✅' if alice_connected else '❌'}")
    print(f"   Bob WebSocket connection: {'✅' if bob_connected else '❌'}")
    print(f"   Alice move notifications: {alice_moves_received}")
    print(f"   Bob move notifications: {bob_moves_received}")
    print(f"   Gameplay simulation: {'✅' if gameplay_success else '❌'}")
    print(f"   Turn enforcement: {'✅' if gameplay_success else '❌'}")
    
    overall_success = (
        alice_connected and bob_connected and
        alice_moves_received >= 2 and bob_moves_received >= 2 and 
        gameplay_success
    )
    
    if overall_success:
        print("\n🎉 SUCCESS: Complete browser simulation working perfectly!")
        print("   ✅ Both players can create and join games")
        print("   ✅ WebSocket real-time communication works")
        print("   ✅ Turn-based gameplay enforced correctly")
        print("   ✅ Board synchronization works across browsers")
        print("   ✅ All move notifications received")
        print("\n🚀 READY FOR REAL USERS!")
    else:
        print("\n❌ ISSUES DETECTED:")
        if not alice_connected or not bob_connected:
            print("   - WebSocket connection problems")
        if alice_moves_received < 2 or bob_moves_received < 2:
            print("   - Move notification problems")
        if not gameplay_success:
            print("   - Gameplay or turn enforcement problems")
    
    return overall_success

if __name__ == "__main__":
    try:
        result = asyncio.run(test_complete_browser_simulation())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
