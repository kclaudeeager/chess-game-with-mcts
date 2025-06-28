"""
Game session management for chess games.
"""
import time
import uuid
from enum import Enum
from typing import Dict, Optional, Set
from threading import Lock
from models.chess_board import ChessBoard, Color, GameMode, GameResult
from engines.mcts import ChessMCTS
from engines.rl_mcts import RLEnhancedMCTS




class GameSession:
    """Represents a single chess game session with independent state"""
    
    def __init__(self, session_id: str, mode: GameMode = GameMode.HUMAN_VS_AI):
        self.session_id = session_id
        self.mode = mode
        self.board = ChessBoard()
        self.created_at = time.time()
        self.last_activity = time.time()
        self.player_white = None
        self.player_black = None
        self._mcts_engine = None
        self._rl_mcts_engine = None
        self.invitation_code = None
        self.connected_players: Set[str] = set()
        self.game_started = False
        self.use_rl_engine = False
        self.game_recorder_id = None
        self.opponent_session_id = None
    
    @property
    def mcts_engine(self):
        """Lazy initialization of MCTS engine"""
        if self.use_rl_engine:
            if self._rl_mcts_engine is None:
                self._rl_mcts_engine = RLEnhancedMCTS(
                    time_limit=6.0,
                    max_simulations=3000,
                    max_depth=40,
                    rl_weight=0.3,
                    data_recorder=None  # Will be set by global instance
                )
            return self._rl_mcts_engine
        else:
            if self._mcts_engine is None:
                self._mcts_engine = ChessMCTS(
                    time_limit=6.0,
                    max_simulations=3000,
                    max_depth=40
                )
            return self._mcts_engine
    
    def enable_rl_enhancement(self, use_rl: bool = True):
        """Enable or disable RL-enhanced MCTS"""
        self.use_rl_engine = use_rl
        if use_rl and self.game_recorder_id is None:
            # Start recording for RL training
            if hasattr(self.mcts_engine, 'start_game_recording'):
                self.mcts_engine.start_game_recording(self.session_id, self.mode.value)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_activity) > (timeout_hours * 3600)
    
    def add_player(self, player_name: str, color: Optional[Color] = None):
        """Add a player to the session"""
        if color == Color.WHITE or (color is None and self.player_white is None):
            self.player_white = player_name
        elif color == Color.BLACK or (color is None and self.player_black is None):
            self.player_black = player_name
        
        # Start game if both players are present in human vs human mode
        if (self.mode == GameMode.HUMAN_VS_HUMAN and 
            self.player_white and self.player_black and 
            not self.game_started):
            self.game_started = True
    
    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int, 
                  special_move_type=None, promotion_piece=None) -> bool:
        """Make a move in the game"""
        self.update_activity()
        success = self.board.make_move(
            from_row, from_col, to_row, to_col, 
            special_move_type, promotion_piece
        )
        
        # Record move for RL if using RL engine
        if success and self.use_rl_engine and hasattr(self.mcts_engine, 'move_number'):
            self.mcts_engine.move_number += 1
        
        return success
    
    def get_ai_move(self) -> Optional[Dict]:
        """Get AI move for Human vs AI mode"""
        print(f"🔍 get_ai_move called - Mode: {self.mode}, Current player: {self.board.current_player}")
        print(f"🔧 RL engine enabled: {self.use_rl_engine}")
        
        if self.mode == GameMode.HUMAN_VS_AI and self.board.current_player == Color.BLACK:
            print(f"🤖 AI conditions met, calling MCTS engine...")
            self.update_activity()
            legal_moves = self.board.get_all_legal_moves()
            print(f"📝 Legal moves for AI: {len(legal_moves)}")
            if legal_moves:
                print(f"🎯 First few legal moves: {legal_moves[:3]}")
            
            # Debug: Check which engine we're using
            engine = self.mcts_engine
            print(f"🏭 Using engine: {type(engine).__name__}")
            
            ai_move = engine.search(self.board)
            print(f"🤖 MCTS returned: {ai_move}")
            print(f"🔍 Move type: {type(ai_move)}")
            return ai_move
        else:
            print(f"❌ AI conditions not met - Mode: {self.mode}, Player: {self.board.current_player}")
        
        return None
    
    def reset_game(self):
        """Reset the game session"""
        self.board = ChessBoard()
        self.update_activity()
        self.game_started = False
        
        # Restart RL recording if using RL engine
        if self.use_rl_engine and hasattr(self.mcts_engine, 'start_game_recording'):
            self.mcts_engine.start_game_recording(self.session_id, self.mode.value)
    
    def finish_game(self, result: str):
        """Mark game as finished and record final result for RL"""
        if self.use_rl_engine and hasattr(self.mcts_engine, 'record_game_outcome'):
            self.mcts_engine.record_game_outcome(result, self.board)
    
    def get_game_state(self) -> Dict:
        """Get current game state"""
        return self.to_dict()
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary for JSON serialization"""
        board_data = self.board.to_dict()
        
        # Add legal moves to the response
        legal_moves = self.board.get_all_legal_moves()
        board_data['legal_moves'] = legal_moves
        
        return {
            **board_data,
            'session_id': self.session_id,
            'mode': self.mode.value,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'player_white': self.player_white,
            'player_black': self.player_black,
            'game_started': self.game_started,
            'invitation_code': self.invitation_code,
            'connected_players': len(self.connected_players),
            'use_rl_engine': self.use_rl_engine,
            'opponent_session_id': self.opponent_session_id
        }


class SessionManager:
    """Manages multiple game sessions with better isolation"""
    
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.session_lock = Lock()
        self.cleanup_interval = 1800  # 30 minutes
        self.last_cleanup = time.time()
        self.max_sessions = 1000
    
    def create_session(self, mode: GameMode = GameMode.HUMAN_VS_AI, 
                      use_rl: bool = False) -> str:
        """Create a new game session"""
        with self.session_lock:
            # Cleanup before creating new sessions
            self.cleanup_expired_sessions()
            
            # Prevent too many sessions
            if len(self.sessions) >= self.max_sessions:
                self.cleanup_expired_sessions(force=True)
            
            session_id = str(uuid.uuid4())
            while session_id in self.sessions:
                session_id = str(uuid.uuid4())
            
            session = GameSession(session_id, mode)
            if use_rl:
                session.enable_rl_enhancement(True)
            
            self.sessions[session_id] = session
            print(f"🎯 Created new session: {session_id[:8]}... (Mode: {mode.value}, RL: {use_rl})")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get an existing session"""
        with self.session_lock:
            if not session_id or session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            session.update_activity()
            return session
    
    def get_or_create_session(self, session_id: str, 
                             mode: GameMode = GameMode.HUMAN_VS_AI) -> GameSession:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if session:
            return session
        
        # Create new session with the provided ID (for WebSocket compatibility)
        with self.session_lock:
            session = GameSession(session_id, mode)
            self.sessions[session_id] = session
            return session
    
    def cleanup_expired_sessions(self, force: bool = False):
        """Clean up expired sessions"""
        current_time = time.time()
        cleanup_threshold = self.cleanup_interval if not force else 0
        
        if current_time - self.last_cleanup > cleanup_threshold:
            with self.session_lock:
                timeout_hours = 2 if force else 24
                expired_sessions = [
                    sid for sid, session in self.sessions.items() 
                    if session.is_expired(timeout_hours)
                ]
                
                for sid in expired_sessions:
                    session = self.sessions[sid]
                    if session.use_rl_engine:
                        session.finish_game("expired")
                    del self.sessions[sid]
                
                self.last_cleanup = current_time
                if expired_sessions:
                    print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)
    
    def get_session_info(self) -> Dict:
        """Get detailed session information"""
        with self.session_lock:
            active_sessions = 0
            human_vs_ai = 0
            human_vs_human = 0
            rl_sessions = 0
            
            for session in self.sessions.values():
                if not session.is_expired():
                    active_sessions += 1
                    if session.mode == GameMode.HUMAN_VS_AI:
                        human_vs_ai += 1
                    else:
                        human_vs_human += 1
                    if session.use_rl_engine:
                        rl_sessions += 1
            
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": active_sessions,
                "human_vs_ai_sessions": human_vs_ai,
                "human_vs_human_sessions": human_vs_human,
                "rl_enhanced_sessions": rl_sessions
            }
