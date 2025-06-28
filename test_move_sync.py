#!/usr/bin/env python3
"""
Test multiplayer move synchronization with persistent WebSocket connections.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

async def test_move_synchronization():
    """Test that moves are synchronized between both players via WebSocket"""
    print("🔄 Testing Multiplayer Move Synchronization")
    print("=" * 50)
    
    # Step 1: Setup game
    print("1️⃣ Setting up multiplayer game...")
    invitation_response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "HostPlayer",
        "use_rl_engine": False
    })
    
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    print(f"   Invitation code: {invitation_code}")
    
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "GuestPlayer"
    })
    
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"   Session ID: {session_id}")
    print("✅ Game setup complete")
    
    # Step 2: Test move synchronization with persistent connections
    print("\n2️⃣ Testing move synchronization...")
    
    host_messages = []
    guest_messages = []
    test_completed = False
    
    async def host_websocket():
        nonlocal host_messages, test_completed
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   🔗 Host WebSocket connected")
                
                # Listen for messages
                while not test_completed:
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
        nonlocal guest_messages, test_completed
        ws_url = f"ws://localhost:8000/ws/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   🔗 Guest WebSocket connected")
                
                # Listen for messages
                while not test_completed:
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
    
    async def make_test_moves():
        nonlocal test_completed
        
        # Wait for WebSocket connections to establish
        await asyncio.sleep(2)
        
        # Move sequence
        moves = [
            ("White", [6, 4], [4, 4], "e2-e4"),
            ("Black", [1, 4], [3, 4], "e7-e5"),
            ("White", [7, 6], [5, 5], "Ng1-f3"),
        ]
        
        for i, (player, from_pos, to_pos, notation) in enumerate(moves):
            print(f"   {i+1}. {player}: {notation}")
            
            move_response = requests.post(f"{API_BASE}/game/move?session_id={session_id}", json={
                "from": from_pos,
                "to": to_pos
            })
            
            if move_response.ok:
                print(f"      ✅ Move successful")
                # Wait for WebSocket messages to propagate
                await asyncio.sleep(1)
            else:
                print(f"      ❌ Move failed: {move_response.status_code}")
                break
        
        # Wait a bit more for any remaining messages
        await asyncio.sleep(3)
        test_completed = True
        print("   🏁 Test moves completed")
    
    # Run all tasks concurrently
    await asyncio.gather(
        host_websocket(),
        guest_websocket(),
        make_test_moves(),
        return_exceptions=True
    )
    
    # Step 3: Analyze results
    print("\n3️⃣ Analyzing synchronization results...")
    print(f"   Host received {len(host_messages)} messages")
    print(f"   Guest received {len(guest_messages)} messages")
    
    # Check for move_made messages
    host_move_messages = [msg for msg in host_messages if msg.get('type') == 'move_made']
    guest_move_messages = [msg for msg in guest_messages if msg.get('type') == 'move_made']
    
    print(f"   Host move notifications: {len(host_move_messages)}")
    print(f"   Guest move notifications: {len(guest_move_messages)}")
    
    # Step 4: Verify final board state
    print("\n4️⃣ Verifying final board state...")
    final_state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if final_state_response.ok:
        final_state = final_state_response.json()
        board = final_state['board']
        
        # Check key positions
        e4_piece = board[4][4]  # Should have white pawn
        e5_piece = board[3][4]  # Should have black pawn
        f3_piece = board[5][5]  # Should have white knight
        
        print(f"   e4 square: {e4_piece}")
        print(f"   e5 square: {e5_piece}")
        print(f"   f3 square: {f3_piece}")
        
        moves_correct = (
            e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P' and
            e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P' and
            f3_piece and f3_piece.get('color') == 'white' and f3_piece.get('type') == 'N'
        )
        
        if moves_correct:
            print("   ✅ Board state shows all moves executed correctly")
        else:
            print("   ❌ Board state doesn't match expected moves")
    else:
        print(f"   ❌ Failed to get final state: {final_state_response.status_code}")
        moves_correct = False
    
    # Step 5: Overall result
    print("\n📊 Synchronization Test Results:")
    websocket_sync = len(host_move_messages) > 0 and len(guest_move_messages) > 0
    board_sync = moves_correct
    
    print(f"   WebSocket synchronization: {'✅' if websocket_sync else '❌'}")
    print(f"   Board state synchronization: {'✅' if board_sync else '❌'}")
    
    if websocket_sync and board_sync:
        print("\n🎉 SUCCESS: Multiplayer move synchronization working perfectly!")
        print("   ✅ Both players receive real-time move notifications")
        print("   ✅ Board state is correctly synchronized")
        print("   ✅ Moves are executed in proper sequence")
        return True
    else:
        print("\n❌ FAILURE: Synchronization issues detected")
        if not websocket_sync:
            print("   Issue: WebSocket move notifications not working")
        if not board_sync:
            print("   Issue: Board state not synchronized")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_move_synchronization())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
