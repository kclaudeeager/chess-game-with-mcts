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
from data.rl_data import RLDataRecorder

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
rl_data_recorder = RLDataRecorder()

# Initialize RL data recorder
rl_data_recorder.initialize_database()

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
            recent_data = rl_data_recorder.get_recent_data(limit=100)
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
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(
            session_id=session_id,
            mode=request.mode,
            use_rl_engine=request.use_rl_engine,
            difficulty=request.difficulty
        )
        
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
        invitation = invitation_manager.get_invitation(invitation_code)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        session = session_manager.create_session(
            session_id=session_id,
            mode=GameMode.HUMAN_VS_HUMAN,
            use_rl_engine=invitation.use_rl_engine,
            player_white=invitation.host_name,
            player_black=request.player_name
        )
        
        return SessionInfoResponse(
            session_id=session_id,
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
    invitation = invitation_manager.get_invitation(invitation_code)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    return {
        "invitation_code": invitation.code,
        "host_name": invitation.host_name,
        "use_rl_engine": invitation.use_rl_engine,
        "expires_at": invitation.expires_at.isoformat(),
        "is_expired": invitation.is_expired()
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
        await websocket_manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await websocket_manager.disconnect(websocket, session_id)

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

# ===== MAIN ENTRY POINT =====

if __name__ == "__main__":
    print("🚀 Starting Modular Chess Engine Server...")
    print("🌐 Open your browser to: http://localhost:8000")
    print("💡 Features: Full Chess Rules, MCTS AI, RL Enhancement, Real-time Multiplayer")
    print("🎯 Modular Architecture: Clean, maintainable, production-ready!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
