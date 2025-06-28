"""
Multiplayer features: invitations and WebSocket management.
"""
import json
import random
import string
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Set, Optional
from fastapi import WebSocket


class InvitationManager:
    """Manages invitation codes for Human vs Human games"""
    
    def __init__(self):
        self.invitations: Dict[str, Dict] = {}
        self.invitation_lock = Lock()
        self.invitation_expiry = 3600  # 1 hour
    
    def create_invitation(self, host_name: str = "Player 1", use_rl_engine: bool = False) -> object:
        """Create a new invitation code and return invitation object"""
        import uuid
        from datetime import datetime, timedelta
        
        with self.invitation_lock:
            code = self._generate_invitation_code()
            while code in self.invitations:
                code = self._generate_invitation_code()
            
            # Create invitation object-like structure
            class Invitation:
                def __init__(self, code, host_name, use_rl_engine):
                    self.code = code
                    self.host_name = host_name
                    self.use_rl_engine = use_rl_engine
                    self.expires_at = datetime.now() + timedelta(seconds=3600)
                    self.created_at = datetime.now()
                
                def is_expired(self):
                    return datetime.now() > self.expires_at
            
            invitation = Invitation(code, host_name, use_rl_engine)
            
            self.invitations[code] = {
                'host_session_id': str(uuid.uuid4()),
                'host_player_name': host_name,
                'guest_session_id': None,
                'guest_player_name': None,
                'created_at': time.time(),
                'status': 'waiting',
                'use_rl_engine': use_rl_engine,
                'invitation_obj': invitation
            }
            
            print(f"🎫 Created invitation code: {code} for host {host_name}")
            return invitation
    
    def _generate_invitation_code(self) -> str:
        """Generate a random invitation code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    def join_game(self, invitation_code: str, guest_session_id: str, 
                  guest_player_name: str = "Player 2") -> Dict:
        """Join a game using invitation code"""
        with self.invitation_lock:
            if invitation_code not in self.invitations:
                return {"success": False, "message": "Invalid invitation code"}
            
            invitation = self.invitations[invitation_code]
            
            # Check if invitation has expired
            if time.time() - invitation['created_at'] > self.invitation_expiry:
                del self.invitations[invitation_code]
                return {"success": False, "message": "Invitation has expired"}
            
            # Check if game is already full
            if invitation['guest_session_id']:
                return {"success": False, "message": "Game is already full"}
            
            # Join the game
            invitation['guest_session_id'] = guest_session_id
            invitation['guest_player_name'] = guest_player_name
            invitation['status'] = 'in_progress'
            
            print(f"👥 Player {guest_player_name} joined game with code {invitation_code}")
            
            return {
                "success": True,
                "host_session_id": invitation['host_session_id'],
                "host_player": invitation['host_player_name'],
                "message": f"Successfully joined {invitation['host_player_name']}'s game!"
            }
    
    def join_invitation(self, invitation_code: str, player_name: str) -> str:
        """Join an invitation and return session_id"""
        result = self.join_game(invitation_code, "", player_name)
        if result["success"]:
            # Return a new session ID for the joined game
            import uuid
            return str(uuid.uuid4())
        else:
            raise ValueError(result["message"])
    
    def get_invitation_info(self, invitation_code: str) -> Optional[Dict]:
        """Get information about an invitation"""
        with self.invitation_lock:
            if invitation_code not in self.invitations:
                return None
            
            invitation = self.invitations[invitation_code]
            
            # Check if expired
            if time.time() - invitation['created_at'] > self.invitation_expiry:
                del self.invitations[invitation_code]
                return None
            
            return invitation.copy()
    
    def get_active_invitation_count(self) -> int:
        """Get count of active (non-expired) invitations"""
        with self.invitation_lock:
            current_time = time.time()
            active_count = 0
            for invitation in self.invitations.values():
                if current_time - invitation['created_at'] <= self.invitation_expiry:
                    active_count += 1
            return active_count
    
    def cleanup_expired_invitations(self):
        """Clean up expired invitations"""
        with self.invitation_lock:
            current_time = time.time()
            expired_codes = [
                code for code, invitation in self.invitations.items()
                if current_time - invitation['created_at'] > self.invitation_expiry
            ]
            
            for code in expired_codes:
                del self.invitations[code]
            
            if expired_codes:
                print(f"🧹 Cleaned up {len(expired_codes)} expired invitations")


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.websocket_to_session: Dict[WebSocket, str] = {}
        self.connection_lock = Lock()
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Add a WebSocket connection for a session"""
        await websocket.accept()
        with self.connection_lock:
            self.connections[session_id].add(websocket)
            self.websocket_to_session[websocket] = session_id
        print(f"🔗 WebSocket connected for session {session_id[:8]}...")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        with self.connection_lock:
            session_id = self.websocket_to_session.pop(websocket, None)
            if session_id and websocket in self.connections[session_id]:
                self.connections[session_id].remove(websocket)
                if not self.connections[session_id]:
                    del self.connections[session_id]
        if session_id:
            print(f"❌ WebSocket disconnected for session {session_id[:8]}...")
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all connections for a session"""
        if session_id not in self.connections:
            return
        
        disconnected = []
        message_json = json.dumps(message)
        
        for websocket in self.connections[session_id].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                print(f"⚠️ Failed to send message to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_to_game(self, session_id: str, message: dict):
        """Alias for broadcast_to_session for compatibility"""
        await self.broadcast_to_session(session_id, message)
    
    def add_connection(self, session_id: str, websocket: WebSocket):
        """Add connection (sync version for compatibility)"""
        with self.connection_lock:
            self.connections[session_id].add(websocket)
            self.websocket_to_session[websocket] = session_id
    
    def remove_connection(self, session_id: str):
        """Remove all connections for a session"""
        with self.connection_lock:
            if session_id in self.connections:
                for ws in self.connections[session_id].copy():
                    self.websocket_to_session.pop(ws, None)
                del self.connections[session_id]
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.connections.values())
