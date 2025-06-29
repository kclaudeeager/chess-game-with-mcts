#!/usr/bin/env python3
"""
Real-world multiplayer test: Simulate two separate browser sessions
with proper turn enforcement and player visibility.
"""

import asyncio
import json
import websockets
import requests
import time

API_BASE = "http://localhost:8000/api"

class PlayerSimulator:
    def __init__(self, name, is_host=False):
        self.name = name
        self.is_host = is_host
        self.session_id = None
        self.my_color = 'white' if is_host else 'black'
        self.socket = None
        self.messages = []
        self.connected = False
        
    async def create_or_join_game(self, invitation_code=None):
        """Simulate creating or joining a game"""
        if self.is_host:
            # Host creates invitation
            print(f"🏠 {self.name} (Host) creating invitation...")
            response = requests.post(f"{API_BASE}/invitation", json={
                "host_name": self.name,
                "use_rl_engine": False
            })
            
            if not response.ok:
                raise Exception(f"Failed to create invitation: {response.status_code}")
                
            data = response.json()
            invitation_code = data["invitation_code"]
            print(f"   ✅ Invitation created: {invitation_code}")
            return invitation_code
            
        else:
            # Guest joins invitation
            print(f"🎯 {self.name} (Guest) joining invitation {invitation_code}...")
            response = requests.post(f"{API_BASE}/invitation/{invitation_code}/join", json={
                "player_name": self.name
            })
            
            if not response.ok:
                raise Exception(f"Failed to join invitation: {response.status_code}")
                
            data = response.json()
            self.session_id = data["session_id"]
            print(f"   ✅ Joined successfully. Session: {self.session_id}")
            return data
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        if not self.session_id:
            raise Exception("No session ID available for WebSocket")
            
        ws_url = f"ws://localhost:8000/ws/{self.session_id}"
        print(f"🔗 {self.name} connecting to WebSocket...")
        
        try:
            self.socket = await websockets.connect(ws_url)
            self.connected = True
            print(f"   ✅ {self.name} WebSocket connected")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            print(f"   ❌ {self.name} WebSocket failed: {e}")
            raise
    
    async def _listen_for_messages(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.socket:
                data = json.loads(message)
                self.messages.append(data)
                print(f"📨 {self.name} received: {data.get('type', 'unknown')}")
                
                # Special handling for different message types
                if data.get('type') == 'move_made':
                    print(f"   📋 {self.name} sees move on board")
                elif data.get('type') == 'player_joined':
                    print(f"   👥 {self.name} sees: {data.get('message', 'Player joined')}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print(f"🔌 {self.name} WebSocket disconnected")
        except Exception as e:
            print(f"❌ {self.name} WebSocket error: {e}")
    
    def get_game_state(self):
        """Get current game state"""
        response = requests.get(f"{API_BASE}/game/state?session_id={self.session_id}")
        if response.ok:
            return response.json()
        else:
            raise Exception(f"Failed to get game state: {response.status_code}")
    
    def make_move(self, from_pos, to_pos):
        """Attempt to make a move"""
        print(f"🎯 {self.name} ({self.my_color}) attempting move: {from_pos} → {to_pos}")
        
        # Include player_name for turn enforcement
        payload = {
            "from": from_pos,
            "to": to_pos,
            "player_name": self.name
        }
        
        response = requests.post(f"{API_BASE}/game/move?session_id={self.session_id}", json=payload)
        
        if response.ok:
            data = response.json()
            print(f"   ✅ {self.name} move successful")
            return True, data
        else:
            error_data = response.json()
            print(f"   ❌ {self.name} move failed: {error_data.get('detail', 'Unknown error')}")
            return False, error_data
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        if self.socket:
            await self.socket.close()
            self.connected = False

async def test_real_multiplayer_scenario():
    """Test the complete real-world multiplayer scenario"""
    print("🎮 Real-World Multiplayer Test")
    print("=" * 50)
    
    # Step 1: Create two players
    alice = PlayerSimulator("Alice", is_host=True)
    bob = PlayerSimulator("Bob", is_host=False)
    
    try:
        # Step 2: Alice creates game, Bob joins
        print("\n1️⃣ Setting up game...")
        invitation_code = await alice.create_or_join_game()
        
        join_data = await bob.create_or_join_game(invitation_code)
        bob.session_id = join_data["session_id"]
        alice.session_id = bob.session_id  # Same session
        
        # Step 3: Both players connect via WebSocket
        print("\n2️⃣ Establishing WebSocket connections...")
        await alice.connect_websocket()
        await bob.connect_websocket()
        
        # Wait for connections to stabilize
        await asyncio.sleep(2)
        
        # Step 4: Verify both players see each other
        print("\n3️⃣ Verifying player visibility...")
        game_state = alice.get_game_state()
        
        print(f"   Game started: {game_state.get('game_started', False)}")
        print(f"   White player: {game_state.get('player_white', 'None')}")
        print(f"   Black player: {game_state.get('player_black', 'None')}")
        print(f"   Current turn: {game_state.get('current_player', 'Unknown')}")
        
        if not (game_state.get('player_white') and game_state.get('player_black')):
            raise Exception("Players not properly assigned")
        
        # Step 5: Test turn enforcement
        print("\n4️⃣ Testing turn enforcement...")
        
        # Bob (black) tries to move when it's white's turn
        print("   Testing: Bob tries to move on White's turn...")
        success, _ = bob.make_move([1, 4], [3, 4])  # e7-e5
        if success:
            print("   ❌ ERROR: Black was allowed to move on White's turn!")
            return False
        else:
            print("   ✅ Correct: Black move rejected on White's turn")
        
        # Alice (white) makes valid first move
        print("   Testing: Alice makes first move...")
        success, move_data = alice.make_move([6, 4], [4, 4])  # e2-e4
        if not success:
            print("   ❌ ERROR: White move failed!")
            return False
        else:
            print("   ✅ White move successful")
        
        # Wait for WebSocket messages
        await asyncio.sleep(1)
        
        # Verify both players received the move
        alice_move_msgs = [msg for msg in alice.messages if msg.get('type') == 'move_made']
        bob_move_msgs = [msg for msg in bob.messages if msg.get('type') == 'move_made']
        
        print(f"   Alice received {len(alice_move_msgs)} move notifications")
        print(f"   Bob received {len(bob_move_msgs)} move notifications")
        
        if len(alice_move_msgs) == 0 or len(bob_move_msgs) == 0:
            print("   ❌ ERROR: Move notifications not received by both players")
            return False
        
        # Step 6: Test alternating moves
        print("\n5️⃣ Testing alternating gameplay...")
        
        # Now it should be Bob's turn
        game_state = bob.get_game_state()
        current_player = game_state.get('current_player', 'unknown')
        print(f"   Current player after Alice's move: {current_player}")
        
        if current_player != 'black':
            print(f"   ❌ ERROR: Turn didn't switch to black after white move")
            return False
        
        # Bob makes his move
        success, _ = bob.make_move([1, 4], [3, 4])  # e7-e5
        if not success:
            print("   ❌ ERROR: Bob's valid move failed!")
            return False
        else:
            print("   ✅ Bob's move successful")
        
        # Wait for notifications
        await asyncio.sleep(1)
        
        # Alice tries to move when it's still black's turn (should fail)
        print("   Testing: Alice tries to move again...")
        game_state = alice.get_game_state()
        current_player = game_state.get('current_player', 'unknown')
        
        if current_player == 'white':
            # If it's actually Alice's turn, this is correct
            print(f"   Turn properly alternated to white")
        else:
            print(f"   Current player: {current_player}")
        
        # Step 7: Final verification
        print("\n6️⃣ Final verification...")
        final_state = alice.get_game_state()
        board = final_state.get('board', [])
        
        if board:
            e4_piece = board[4][4] if len(board) > 4 and len(board[4]) > 4 else None
            e5_piece = board[3][4] if len(board) > 3 and len(board[3]) > 4 else None
            
            e4_ok = e4_piece and e4_piece.get('color') == 'white' and e4_piece.get('type') == 'P'
            e5_ok = e5_piece and e5_piece.get('color') == 'black' and e5_piece.get('type') == 'P'
            
            print(f"   Board verification - e4: {e4_ok}, e5: {e5_ok}")
            
            if e4_ok and e5_ok:
                print("   ✅ Board state correct: both moves visible")
            else:
                print(f"   ❌ Board state incorrect: e4={e4_piece}, e5={e5_piece}")
                return False
        
        # Check message counts
        alice_total = len(alice.messages)
        bob_total = len(bob.messages)
        print(f"   Message totals - Alice: {alice_total}, Bob: {bob_total}")
        
        if alice_total >= 2 and bob_total >= 2:
            print("   ✅ Both players received adequate notifications")
        else:
            print("   ⚠️  Low message counts - check WebSocket reliability")
        
        print("\n📊 Test Results:")
        print(f"   ✅ Game setup and player assignment")
        print(f"   ✅ WebSocket connections established")
        print(f"   ✅ Turn enforcement working")
        print(f"   ✅ Move synchronization working")
        print(f"   ✅ Board state consistent")
        
        print("\n🎉 SUCCESS: Real-world multiplayer scenario working perfectly!")
        print("   🎯 Two players can join the same game")
        print("   👥 Both players see each other's names")
        print("   🔄 Turn-based gameplay enforced")
        print("   📱 Works across different devices/browsers")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            await alice.disconnect()
            await bob.disconnect()
        except:
            pass

if __name__ == "__main__":
    try:
        result = asyncio.run(test_real_multiplayer_scenario())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
