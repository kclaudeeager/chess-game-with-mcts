#!/usr/bin/env python3
"""
Real multiplayer UI debugging script.
This will test actual browser communication by creating a game session
and providing detailed logging to see exactly where the communication breaks down.
"""

import asyncio
import json
import time
import threading
from flask import Flask
from main import app, socketio
import requests
import websocket
import logging

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealMultiplayerTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.socketio_url = "ws://localhost:5000/socket.io/?EIO=4&transport=websocket"
        self.server_thread = None
        self.session_id = None
        self.player1_ws = None
        self.player2_ws = None
        self.received_messages_p1 = []
        self.received_messages_p2 = []
        
    def start_server(self):
        """Start the Flask-SocketIO server in a separate thread"""
        def run_server():
            print("🚀 Starting server on localhost:5000...")
            socketio.run(app, host='localhost', port=5000, debug=False, allow_unsafe_werkzeug=True)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(3)
        
        # Test if server is responding
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            print(f"✅ Server is responding: {response.status_code}")
            return True
        except Exception as e:
            print(f"❌ Server not responding: {e}")
            return False

    def create_game_session(self):
        """Create a new game session via API"""
        try:
            print("\n🎮 Creating new game session...")
            response = requests.post(f"{self.base_url}/create_session", 
                                   json={'mode': 'human_vs_human'}, 
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data['session_id']
                print(f"✅ Session created: {self.session_id}")
                return True
            else:
                print(f"❌ Failed to create session: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error creating session: {e}")
            return False

    def test_api_endpoints(self):
        """Test all relevant API endpoints"""
        print("\n🔍 Testing API endpoints...")
        
        # Test session info
        try:
            response = requests.get(f"{self.base_url}/session/{self.session_id}")
            print(f"📊 Session info: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Session info error: {e}")
        
        # Test join game as player 1
        try:
            response = requests.post(f"{self.base_url}/join_game", 
                                   json={'session_id': self.session_id, 'player_name': 'TestPlayer1'})
            print(f"👤 Player 1 join: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Player 1 join error: {e}")
        
        # Test join game as player 2
        try:
            response = requests.post(f"{self.base_url}/join_game", 
                                   json={'session_id': self.session_id, 'player_name': 'TestPlayer2'})
            print(f"👤 Player 2 join: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Player 2 join error: {e}")
        
        # Test session info again
        try:
            response = requests.get(f"{self.base_url}/session/{self.session_id}")
            print(f"📊 Updated session info: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Updated session info error: {e}")

    def on_message_p1(self, ws, message):
        """Handle WebSocket messages for player 1"""
        print(f"🟦 Player 1 received: {message}")
        self.received_messages_p1.append(message)

    def on_message_p2(self, ws, message):
        """Handle WebSocket messages for player 2"""
        print(f"🟩 Player 2 received: {message}")
        self.received_messages_p2.append(message)

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"❌ WebSocket error: {error}")

    def on_open_p1(self, ws):
        """Handle WebSocket connection opened for player 1"""
        print("🟦 Player 1 WebSocket connected")
        # Join the session room
        join_message = {
            "session_id": self.session_id,
            "player_name": "TestPlayer1"
        }
        ws.send(json.dumps(join_message))

    def on_open_p2(self, ws):
        """Handle WebSocket connection opened for player 2"""
        print("🟩 Player 2 WebSocket connected")
        # Join the session room
        join_message = {
            "session_id": self.session_id,
            "player_name": "TestPlayer2"
        }
        ws.send(json.dumps(join_message))

    def test_websocket_communication(self):
        """Test WebSocket communication between two clients"""
        print("\n🔌 Testing WebSocket communication...")
        
        try:
            # Create WebSocket connections
            print("🟦 Connecting Player 1 WebSocket...")
            self.player1_ws = websocket.WebSocketApp(self.socketio_url,
                                                    on_message=self.on_message_p1,
                                                    on_error=self.on_error,
                                                    on_open=self.on_open_p1)
            
            print("🟩 Connecting Player 2 WebSocket...")
            self.player2_ws = websocket.WebSocketApp(self.socketio_url,
                                                    on_message=self.on_message_p2,
                                                    on_error=self.on_error,
                                                    on_open=self.on_open_p2)
            
            # Start WebSocket connections in threads
            p1_thread = threading.Thread(target=self.player1_ws.run_forever, daemon=True)
            p2_thread = threading.Thread(target=self.player2_ws.run_forever, daemon=True)
            
            p1_thread.start()
            p2_thread.start()
            
            # Wait for connections to establish
            time.sleep(2)
            
            # Test sending a move from player 1
            print("\n🎯 Testing move from Player 1...")
            move_data = {
                "session_id": self.session_id,
                "move": "e2e4",
                "player_name": "TestPlayer1"
            }
            
            response = requests.post(f"{self.base_url}/make_move", json=move_data)
            print(f"📤 Move response: {response.status_code} - {response.json()}")
            
            # Wait for WebSocket messages to be received
            time.sleep(2)
            
            print(f"\n📥 Player 1 received {len(self.received_messages_p1)} messages")
            print(f"📥 Player 2 received {len(self.received_messages_p2)} messages")
            
            return True
            
        except Exception as e:
            print(f"❌ WebSocket test error: {e}")
            return False

    def generate_browser_test_urls(self):
        """Generate URLs for manual browser testing"""
        print(f"\n🌐 Browser Test URLs:")
        print(f"Main UI: {self.base_url}/")
        print(f"Session: {self.base_url}/?session_id={self.session_id}")
        print(f"Player 1: {self.base_url}/?session_id={self.session_id}&player_name=TestPlayer1")
        print(f"Player 2: {self.base_url}/?session_id={self.session_id}&player_name=TestPlayer2")
        
        return [
            f"{self.base_url}/?session_id={self.session_id}&player_name=TestPlayer1",
            f"{self.base_url}/?session_id={self.session_id}&player_name=TestPlayer2"
        ]

    def run_comprehensive_test(self):
        """Run all tests"""
        print("🧪 Starting comprehensive real multiplayer test...\n")
        
        # Start server
        if not self.start_server():
            print("❌ Failed to start server")
            return False
        
        # Create session
        if not self.create_game_session():
            print("❌ Failed to create session")
            return False
        
        # Test API endpoints
        self.test_api_endpoints()
        
        # Test WebSocket communication
        self.test_websocket_communication()
        
        # Generate browser URLs
        urls = self.generate_browser_test_urls()
        
        print("\n" + "="*50)
        print("🎯 MANUAL TESTING INSTRUCTIONS:")
        print("="*50)
        print("1. Open these URLs in separate browser tabs/windows:")
        for i, url in enumerate(urls, 1):
            print(f"   Tab {i}: {url}")
        print("2. Set game mode to 'Human vs Human' in both tabs")
        print("3. Try making moves in one tab and see if they appear in the other")
        print("4. Check the Players Panel in both tabs")
        print("5. Check browser console for any JavaScript errors")
        print("6. Check Network tab for WebSocket connections")
        print("="*50)
        
        return True

if __name__ == "__main__":
    tester = RealMultiplayerTester()
    tester.run_comprehensive_test()
    
    # Keep the script running so the server stays up for manual testing
    print("\n🏃 Server running for manual testing. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping server...")
