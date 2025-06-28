"""
Clean, modular FastAPI Chess Engine
All chess logic, MCTS, RL, and game management has been moved to separate modules.
This file contains only the FastAPI app setup and API endpoints.
"""

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import uvicorn
import uuid
import asyncio
from threading import Thread
import time

# Import our modular components
from models.chess_board import GameMode, GameResult
from session.game_session import SessionManager
from multiplayer.features import InvitationManager, WebSocketManager
from api.models import (
    CreateSessionRequest, MakeMoveRequest, CreateInvitationRequest,
    JoinSessionRequest, SessionInfoResponse, InvitationResponse
)
from api.websocket_handlers import handle_websocket_message
from data.rl_data import GameDataRecorder

# Initialize FastAPI app
app = FastAPI(
    title="Modular Chess Engine API",
    description="Production-ready chess engine with MCTS, RL, and real-time multiplayer",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="template")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global managers (initialized once)
session_manager = SessionManager()
invitation_manager = InvitationManager()
websocket_manager = WebSocketManager()
rl_data_recorder = GameDataRecorder()

# Initialize RL data recorder
rl_data_recorder._init_database()

# ===== UTILITY FUNCTIONS =====

def cleanup_expired_sessions():
    """Background task to clean up expired sessions and invitations"""
    while True:
        try:
            session_manager.cleanup_expired_sessions()
            invitation_manager.cleanup_expired_invitations()
            time.sleep(60)  # Run every minute
        except Exception as e:
            print(f"❌ Error in cleanup task: {e}")
            time.sleep(60)

def update_rl_engines():
    """Background task to periodically update RL engines with new data"""
    while True:
        try:
            # Get recent game data and update RL engines
            recent_data = rl_data_recorder.get_recent_games(limit=100)
            if recent_data:
                # Update RL engines in active sessions
                for session in session_manager.sessions.values():
                    if hasattr(session, 'rl_mcts_engine') and session.rl_mcts_engine:
                        # Update position history with recent successful patterns
                        for data in recent_data[-10:]:  # Use last 10 entries
                            session.rl_mcts_engine.position_history.append({
                                'position': data['board_state'],
                                'result': 'good' if data['player_won'] else 'neutral'
                            })
                            # Limit history size
                            if len(session.rl_mcts_engine.position_history) > 1000:
                                session.rl_mcts_engine.position_history.popleft()
            
            time.sleep(300)  # Run every 5 minutes
        except Exception as e:
            print(f"❌ Error in RL update task: {e}")
            time.sleep(300)

# Start background tasks
cleanup_thread = Thread(target=cleanup_expired_sessions, daemon=True)
cleanup_thread.start()

rl_update_thread = Thread(target=update_rl_engines, daemon=True) 
rl_update_thread.start()

# ===== MAIN PAGE =====

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main chess game interface"""
    return templates.TemplateResponse("index.html", {"request": request})

# ===== SESSION MANAGEMENT ENDPOINTS =====

@app.post("/api/session", response_model=SessionInfoResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chess game session"""
    try:
        # Convert string mode to enum
        mode = GameMode.HUMAN_VS_AI if request.mode == "human_vs_ai" else GameMode.HUMAN_VS_HUMAN
        session_id = session_manager.create_session(
            mode=mode,
            use_rl=request.use_rl_engine
        )
        
        # Get the created session
        session = session_manager.get_session(session_id)
        
        return SessionInfoResponse(
            session_id=session_id,
            success=True,
            game_state=session.to_dict()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """Get current session state"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfoResponse(
        session_id=session_id,
        success=True,
        game_state=session.to_dict()
    )

@app.post("/api/session/{session_id}/move")
async def make_move(session_id: str, request: MakeMoveRequest):
    """Make a move in the game"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        success = session.make_move(
            request.from_pos[0], request.from_pos[1],
            request.to_pos[0], request.to_pos[1],
            request.promotion.type if request.promotion else None,
            request.promotion.piece if request.promotion else None
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid move")
        
        # Check if game is finished
        game_result = session.board.get_game_result()
        if game_result != GameResult.IN_PROGRESS:
            session.finish_game(game_result.value)
            
            # Record game data for RL if this was an RL-enhanced session
            if session.use_rl_engine:
                try:
                    winner = None
                    if game_result == GameResult.WHITE_WINS:
                        winner = 'white'
                    elif game_result == GameResult.BLACK_WINS:
                        winner = 'black'
                    
                    rl_data_recorder.record_game(
                        board_state=session.board.to_dict(),
                        move_sequence=session.board.move_history,
                        player_won=(winner == 'white'),  # Assuming human is white
                        game_result=game_result.value
                    )
                except Exception as e:
                    print(f"❌ Error recording RL data: {e}")
        
        # Notify WebSocket clients if this is a multiplayer game
        if session.mode == GameMode.HUMAN_VS_HUMAN:
            await websocket_manager.broadcast_to_session(session_id, {
                "type": "move_made",
                "game_state": session.to_dict(),
                "game_result": game_result.value
            })
        
        return {
            "success": True,
            "game_state": session.to_dict(),
            "game_result": game_result.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/ai_move")
async def get_ai_move(session_id: str):
    """Get AI move for Human vs AI mode"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        ai_move = session.get_ai_move()
        if not ai_move:
            raise HTTPException(status_code=400, detail="No AI move available")
        
        # Actually execute the AI move on the board
        move_success = session.make_move(ai_move[0], ai_move[1], ai_move[2], ai_move[3])
        if not move_success:
            raise HTTPException(status_code=500, detail="Failed to execute AI move")
        
        # Check if game is finished after AI move
        game_result = session.board.get_game_result()
        if game_result != GameResult.IN_PROGRESS:
            session.finish_game(game_result.value)
            
            # Record game data for RL
            if session.use_rl_engine:
                try:
                    winner = None
                    if game_result == GameResult.WHITE_WINS:
                        winner = 'white'
                    elif game_result == GameResult.BLACK_WINS:
                        winner = 'black'
                    
                    rl_data_recorder.record_game(
                        board_state=session.board.to_dict(),
                        move_sequence=session.board.move_history,
                        player_won=(winner == 'white'),  # Assuming human is white
                        game_result=game_result.value
                    )
                except Exception as e:
                    print(f"❌ Error recording RL data: {e}")
        
        return {
            "success": True,
            "move": ai_move,
            "game_state": session.to_dict(),
            "game_result": game_result.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset the game session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session.reset_game()
        
        # Notify WebSocket clients if this is a multiplayer game
        if session.mode == GameMode.HUMAN_VS_HUMAN:
            await websocket_manager.broadcast_to_session(session_id, {
                "type": "game_reset",
                "game_state": session.to_dict()
            })
        
        return {
            "success": True,
            "game_state": session.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/join")
async def join_session(session_id: str, request: Request):
    """Join an existing game session"""
    try:
        data = await request.json()
        player_name = data.get("player_name")
        color = data.get("color", "black")  # Default to black for joining players
        
        if not player_name:
            raise HTTPException(status_code=400, detail="player_name is required")
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Add player to session
        if color == "white":
            if session.player_white:
                raise HTTPException(status_code=400, detail="White player already set")
            session.player_white = player_name
        else:
            if session.player_black:
                raise HTTPException(status_code=400, detail="Black player already set")
            session.player_black = player_name
        
        # Update session activity
        session.update_activity()
        
        # Start game if both players are present in human vs human mode
        if (session.mode == GameMode.HUMAN_VS_HUMAN and 
            session.player_white and session.player_black and 
            not session.game_started):
            session.game_started = True
        
        return {
            "success": True,
            "message": f"Player {player_name} joined as {color}",
            "game_state": session.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/settings")
async def update_session_settings(session_id: str, request: Request):
    """Update session settings (e.g., RL engine toggle)"""
    try:
        data = await request.json()
        use_rl_engine = data.get("use_rl_engine", False)
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update RL engine setting and reset engines to ensure clean state
        old_rl_setting = session.use_rl_engine
        session.use_rl_engine = use_rl_engine
        
        # If RL setting changed, reset the engines to ensure clean initialization
        if old_rl_setting != use_rl_engine:
            session._mcts_engine = None
            session._rl_mcts_engine = None
            print(f"🔄 Engines reset due to RL setting change: {old_rl_setting} -> {use_rl_engine}")
        
        session.update_activity()
        
        return {
            "success": True,
            "message": f"RL engine {'enabled' if use_rl_engine else 'disabled'}",
            "use_rl_engine": use_rl_engine
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== MULTIPLAYER ENDPOINTS =====

@app.post("/api/invitation", response_model=InvitationResponse)
async def create_invitation(request: CreateInvitationRequest):
    """Create a game invitation"""
    try:
        invitation = invitation_manager.create_invitation(
            host_name=request.host_name,
            use_rl_engine=request.use_rl_engine
        )
        
        return InvitationResponse(
            success=True,
            invitation_code=invitation.code,
            host_name=invitation.host_name,
            expires_at=invitation.expires_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/invitation/{invitation_code}/join", response_model=SessionInfoResponse)
async def join_invitation(invitation_code: str, request: JoinSessionRequest):
    """Join a game using invitation code"""
    try:
        session_id = invitation_manager.join_invitation(invitation_code, request.player_name)
        
        # Create the actual game session
        invitation_info = invitation_manager.get_invitation_info(invitation_code)
        if not invitation_info:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        # Note: For now, we create a new session_id since create_session generates its own
        # TODO: Update SessionManager to accept custom session_id or use invitation system differently
        actual_session_id = session_manager.create_session(
            mode=GameMode.HUMAN_VS_HUMAN,
            use_rl=invitation_info.get('use_rl_engine', False)
        )
        
        # Get the created session and update player info
        session = session_manager.get_session(actual_session_id)
        if session:
            session.player_white = invitation_info.get('host_player_name', 'Host')
            session.player_black = request.player_name
        
        return SessionInfoResponse(
            session_id=actual_session_id,
            success=True,
            game_state=session.to_dict()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/invitation/{invitation_code}")
async def get_invitation(invitation_code: str):
    """Get invitation details"""
    invitation_info = invitation_manager.get_invitation_info(invitation_code)
    if not invitation_info:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    return {
        "invitation_code": invitation_code,
        "host_name": invitation_info.get('host_player_name', 'Host'),
        "use_rl_engine": invitation_info.get('use_rl_engine', False),
        "created_at": invitation_info.get('created_at', time.time()),
        "is_expired": time.time() - invitation_info.get('created_at', 0) > 3600
    }

# ===== WEBSOCKET ENDPOINTS =====

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time game communication"""
    await websocket_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Handle the message using our modular handler
            response = await handle_websocket_message(
                session_id, data, session_manager, invitation_manager
            )
            
            # Send response back to client
            if response:
                await websocket.send_text(response)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

# ===== ADMIN/STATS ENDPOINTS =====

@app.get("/api/stats")
async def get_stats():
    """Get server statistics"""
    session_info = session_manager.get_session_info()
    invitation_count = invitation_manager.get_active_invitation_count()
    
    return {
        "sessions": session_info,
        "active_invitations": invitation_count,
        "websocket_connections": len(websocket_manager.active_connections),
        "rl_data_entries": rl_data_recorder.get_total_entries()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "full_chess_rules",
            "mcts_ai",
            "rl_enhancement", 
            "real_time_multiplayer",
            "invitation_system",
            "session_management"
        ]
    }

# ===== COMPATIBILITY ENDPOINTS (for existing frontend) =====

@app.post("/api/session/create")
async def create_session_legacy(request: Request):
    """Legacy endpoint for session creation - compatibility with existing frontend"""
    try:
        data = await request.json()
        mode_str = data.get("mode", "human_vs_ai")
        use_rl = data.get("use_rl", False)
        
        session_id = str(uuid.uuid4())
        mode = GameMode.HUMAN_VS_AI if mode_str == "human_vs_ai" else GameMode.HUMAN_VS_HUMAN
        session_id = session_manager.create_session(
            mode=mode,
            use_rl=use_rl
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "mode": mode.value,
            "use_rl": use_rl
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/game/state")
async def get_game_state_legacy(session_id: str = None):
    """Legacy endpoint for getting game state - compatibility with existing frontend"""
    if not session_id:
        return {"error": "session_id parameter is required", "status": "error"}
    
    session = session_manager.get_session(session_id)
    if not session:
        return {"error": "Session not found", "status": "error"}
    
    return session.to_dict()

@app.post("/api/game/move")
async def make_move_legacy(request: Request):
    """Legacy endpoint for making moves - compatibility with existing frontend"""
    try:
        # Get session_id from query parameter first, then from body
        session_id = request.query_params.get("session_id")
        
        data = await request.json()
        if not session_id:
            session_id = data.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Handle both old format (from/to arrays) and new format (from_row/from_col/to_row/to_col)
        if "from_row" in data and "from_col" in data and "to_row" in data and "to_col" in data:
            # New format
            from_row = data["from_row"]
            from_col = data["from_col"] 
            to_row = data["to_row"]
            to_col = data["to_col"]
        elif "from" in data and "to" in data:
            # Old format
            from_pos = data["from"]
            to_pos = data["to"]
            from_row, from_col = from_pos[0], from_pos[1]
            to_row, to_col = to_pos[0], to_pos[1]
        else:
            raise HTTPException(status_code=400, detail="Invalid move format")
        
        promotion = data.get("promotion")
        
        success = session.make_move(
            from_row, from_col, to_row, to_col,
            promotion.get("type") if promotion else None,
            promotion.get("piece") if promotion else None
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid move")
        
        # Broadcast move to all connected players via WebSocket
        if session.mode == GameMode.HUMAN_VS_HUMAN:
            move_message = {
                "type": "move_made",
                "data": {
                    "from": [from_row, from_col],
                    "to": [to_row, to_col],
                    "promotion": promotion,
                    "game_state": session.to_dict(),
                    "success": True
                }
            }
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(websocket_manager.broadcast_to_session(session_id, move_message))
            except Exception as e:
                print(f"⚠️ Failed to broadcast move via WebSocket: {e}")
        
        # Check if game is finished
        game_result = session.board.get_game_result()
        if game_result != GameResult.IN_PROGRESS:
            session.finish_game(game_result.value)
        
        return {
            "success": True,
            "game_state": session.to_dict(),
            "game_result": game_result.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/ai_move")
async def get_ai_move_legacy(request: Request):
    """Legacy endpoint for AI moves - compatibility with existing frontend"""
    try:
        # Get session_id from query parameter first, then from body
        session_id = request.query_params.get("session_id")
        
        try:
            data = await request.json()
        except:
            data = {}
            
        if not session_id:
            session_id = data.get("session_id")
        
        print(f"🔍 AI Move Request - Session ID: {session_id}")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        session = session_manager.get_session(session_id)
        if not session:
            print(f"❌ Session not found: {session_id}")
            print(f"📋 Available sessions: {list(session_manager.sessions.keys())}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"✅ Found session: {session_id}")
        print(f"🎯 Current player: {session.board.current_player}")
        print(f"🎮 Game mode: {session.mode}")
        legal_moves = session.board.get_all_legal_moves()
        print(f"📝 Legal moves count: {len(legal_moves)}")
        
        ai_move = session.get_ai_move()
        print(f"🤖 AI move result: {ai_move}")
        print(f"🔍 AI move type: {type(ai_move)}")
        print(f"🔍 AI move truthy: {bool(ai_move)}")
        
        if not ai_move:
            raise HTTPException(status_code=400, detail="No AI move available")
        
        print(f"🔧 AI move validation - Length: {len(ai_move) if hasattr(ai_move, '__len__') else 'N/A'}")
        
        # Actually execute the AI move on the board
        try:
            # Handle both tuple and dictionary formats
            if isinstance(ai_move, dict):
                # Dictionary format: {'from': [3, 3], 'to': [4, 3], ...}
                from_pos = ai_move['from']
                to_pos = ai_move['to']
                move_success = session.make_move(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                print(f"🎯 Dictionary format move execution result: {move_success}")
            else:
                # Tuple format: (from_row, from_col, to_row, to_col)
                move_success = session.make_move(ai_move[0], ai_move[1], ai_move[2], ai_move[3])
                print(f"🎯 Tuple format move execution result: {move_success}")
        except (IndexError, KeyError, TypeError) as e:
            print(f"❌ Error accessing AI move: {e}")
            print(f"🔍 AI move details: {ai_move}")
            print(f"🔍 AI move type: {type(ai_move)}")
            raise HTTPException(status_code=500, detail=f"Invalid AI move format: {ai_move}")
        except Exception as e:
            print(f"❌ Error executing AI move: {e}")
            raise HTTPException(status_code=500, detail=f"Move execution failed: {str(e)}")
        
        if not move_success:
            raise HTTPException(status_code=500, detail="Failed to execute AI move")
        
        # Check if game is finished after AI move
        game_result = session.board.get_game_result()
        if game_result != GameResult.IN_PROGRESS:
            session.finish_game(game_result.value)
        
        return {
            "success": True,
            "move": ai_move,
            "game_state": session.to_dict(),
            "game_result": game_result.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/reset")
async def reset_game_legacy(request: Request):
    """Legacy endpoint for game reset - compatibility with existing frontend"""
    try:
        # Get session_id from query parameter first, then from body
        session_id = request.query_params.get("session_id")
        
        try:
            data = await request.json()
        except:
            data = {}
            
        if not session_id:
            session_id = data.get("session_id")
        
        print(f"🔄 Reset Request - Session ID: {session_id}")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        session = session_manager.get_session(session_id)
        if not session:
            print(f"❌ Session not found for reset: {session_id}")
            print(f"📋 Available sessions: {list(session_manager.sessions.keys())}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"✅ Resetting session: {session_id}")
        session.reset_game()
        print(f"🎯 Reset completed successfully")
        
        return {
            "success": True,
            "game_state": session.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== MAIN ENTRY POINT =====

if __name__ == "__main__":
    print("🚀 Starting Modular Chess Engine Server...")
    print("🌐 Open your browser to: http://localhost:8000")
    print("💡 Features: Full Chess Rules, MCTS AI, RL Enhancement, Real-time Multiplayer")
    print("🎯 Modular Architecture: Clean, maintainable, production-ready!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
