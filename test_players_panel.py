#!/usr/bin/env python3
"""
Test to verify the players panel is displaying correctly
"""
import requests

API_BASE = "http://localhost:8000/api"

def test_players_panel():
    print("👥 Testing Players Panel Display")
    print("=" * 40)
    
    # Create invitation
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
    
    # Bob joins
    join_response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
        "player_name": "Bob"
    })
    
    if not join_response.ok:
        print(f"❌ Failed to join game: {join_response.status_code}")
        return
    
    join_data = join_response.json()
    session_id = join_data["session_id"]
    print(f"✅ Bob joined session: {session_id}")
    
    # Get game state to verify player info
    state_response = requests.get(f"{API_BASE}/game/state?session_id={session_id}")
    if state_response.ok:
        state_data = state_response.json()
        
        print("\n📋 Player Information:")
        print(f"   White Player: {state_data.get('player_white', 'Not set')}")
        print(f"   Black Player: {state_data.get('player_black', 'Not set')}")
        print(f"   Current Turn: {state_data.get('current_player', 'Unknown')}")
        print(f"   Game Started: {state_data.get('game_started', 'Unknown')}")
        print(f"   Game Mode: {state_data.get('mode', 'Unknown')}")
        
        print("\n🌐 To test in browser:")
        print("1. Host (Alice): http://localhost:8000")
        print("   - Change game mode to 'Human vs Human'")
        print("   - Enter name 'Alice' and click 'Set Name'")
        print(f"2. Guest (Bob): http://localhost:8000?invitation_code={invitation_code}")
        print("   - Enter name 'Bob' and click 'Join Game'")
        print("3. Players panel should show both names with turn indicator")
        
        if state_data.get('player_white') and state_data.get('player_black'):
            print("\n✅ Both players are set - players panel should be visible!")
        else:
            print("\n⚠️  Missing player information - check setup")
    else:
        print(f"❌ Failed to get game state: {state_response.status_code}")

if __name__ == "__main__":
    test_players_panel()
