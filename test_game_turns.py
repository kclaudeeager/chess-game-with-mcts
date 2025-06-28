#!/usr/bin/env python3
"""
Test game starting logic and player turn validation.
This checks if both players can make moves when it's their turn.
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_game_starting_and_turns():
    print("🎯 Testing Game Starting Logic and Player Turns")
    print("=" * 50)
    
    # Step 1: Create multiplayer game
    print("📋 Step 1: Setting up multiplayer game...")
    invitation_response = requests.post(f"{API_BASE}/api/invitation", 
                                      json={"host_name": "WhitePlayer", "use_rl_engine": False})
    invitation_data = invitation_response.json()
    invitation_code = invitation_data["invitation_code"]
    
    join_response = requests.post(f"{API_BASE}/api/invitation/{invitation_code}/join",
                                json={"guest_name": "BlackPlayer"})
    join_data = join_response.json()
    session_id = join_data["session_id"]
    
    print(f"✅ Game created: {session_id[:8]}...")
    print(f"   White: {join_data['game_state']['player_white']}")
    print(f"   Black: {join_data['game_state']['player_black']}")
    print(f"   Game started: {join_data['game_state']['game_started']}")
    print(f"   Current player: {join_data['game_state']['current_player']}")
    
    # Step 2: Test that white can make the first move
    print("\n📋 Step 2: Testing white's first move...")
    white_move_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                      json={"from": [6, 4], "to": [4, 4]})
    
    if white_move_response.status_code == 200:
        move_data = white_move_response.json()
        print("✅ White's first move (e2-e4) successful")
        print(f"   Current player after move: {move_data['game_state']['current_player']}")
        print(f"   Game started: {move_data['game_state']['game_started']}")
        print(f"   Move history: {move_data['game_state']['move_history']}")
    else:
        print(f"❌ White's first move failed: {white_move_response.status_code}")
        try:
            error = white_move_response.json()
            print(f"   Error: {error}")
        except:
            print(f"   Raw error: {white_move_response.text}")
        return
    
    # Step 3: Test that black can make the second move
    print("\n📋 Step 3: Testing black's response move...")
    black_move_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                      json={"from": [1, 4], "to": [3, 4]})
    
    if black_move_response.status_code == 200:
        move_data = black_move_response.json()
        print("✅ Black's response move (e7-e5) successful")
        print(f"   Current player after move: {move_data['game_state']['current_player']}")
        print(f"   Move history: {move_data['game_state']['move_history']}")
    else:
        print(f"❌ Black's response move failed: {black_move_response.status_code}")
        try:
            error = black_move_response.json()
            print(f"   Error: {error}")
        except:
            print(f"   Raw error: {black_move_response.text}")
        return
    
    # Step 4: Test that white can make the third move
    print("\n📋 Step 4: Testing white's second move...")
    white_move2_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                       json={"from": [7, 6], "to": [5, 5]})
    
    if white_move2_response.status_code == 200:
        move_data = white_move2_response.json()
        print("✅ White's second move (Ng1-f3) successful")
        print(f"   Current player after move: {move_data['game_state']['current_player']}")
        print(f"   Move history: {move_data['game_state']['move_history']}")
    else:
        print(f"❌ White's second move failed: {white_move2_response.status_code}")
        try:
            error = white_move2_response.json()
            print(f"   Error: {error}")
        except:
            print(f"   Raw error: {white_move2_response.text}")
        return
    
    # Step 5: Test invalid move by wrong player
    print("\n📋 Step 5: Testing invalid move by wrong player...")
    # It should be black's turn, try to make white move
    invalid_move_response = requests.post(f"{API_BASE}/api/game/move?session_id={session_id}",
                                        json={"from": [6, 3], "to": [4, 3]})
    
    if invalid_move_response.status_code == 200:
        print("❌ PROBLEM: Move by wrong player was allowed!")
    else:
        print("✅ Move by wrong player correctly rejected")
        try:
            error = invalid_move_response.json()
            print(f"   Error message: {error.get('detail', 'Unknown error')}")
        except:
            pass
    
    # Step 6: Check final game state
    print("\n📋 Step 6: Final game state...")
    final_state = requests.get(f"{API_BASE}/api/game/state?session_id={session_id}")
    final_data = final_state.json()
    
    print(f"✅ Final state retrieved")
    print(f"   Current player: {final_data['current_player']}")
    print(f"   Move history: {final_data['move_history']}")
    print(f"   Game started: {final_data['game_started']}")
    print(f"   Both players present: White={final_data['player_white']}, Black={final_data['player_black']}")
    
    print("\n🏁 Game starting and turn validation test completed!")
    
    if len(final_data['move_history']) >= 3:
        print("🎉 SUCCESS: Both players can make moves in their turns!")
    else:
        print("⚠️  ISSUE: Not all moves were completed successfully")

if __name__ == "__main__":
    test_game_starting_and_turns()
