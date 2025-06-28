"""
WebSocket endpoint handlers for real-time multiplayer.
"""
import time
from fastapi import WebSocket, WebSocketDisconnect
from models.chess_board import Color, GameMode


async def handle_websocket_connection(websocket: WebSocket, session_id: str,
                                    session_manager, websocket_manager):
    """Handle WebSocket connection for real-time game updates"""
    await websocket.accept()
    
    # Get or create session
    session = session_manager.get_or_create_session(session_id)
    if not session:
        await websocket.close(code=4000, reason="Invalid session")
        return
    
    # Add WebSocket connection to manager
    websocket_manager.add_connection(session_id, websocket)
    session.connected_players.add(session_id)
    
    try:
        # Send current game state
        game_state = {
            "type": "game_state",
            "data": session.get_game_state()
        }
        await websocket.send_json(game_state)
        
        # Listen for messages
        while True:
            try:
                message = await websocket.receive_json()
                await handle_websocket_message(session_id, message, websocket,
                                             session_manager, websocket_manager)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        websocket_manager.disconnect(websocket)
        session.connected_players.discard(session_id)


async def handle_websocket_message(session_id: str, message: dict, websocket: WebSocket,
                                 session_manager, websocket_manager):
    """Handle incoming WebSocket messages"""
    session = session_manager.get_session(session_id)
    if not session:
        return
    
    message_type = message.get("type")
    
    if message_type == "make_move":
        await handle_make_move(session, message, websocket, websocket_manager)
    
    elif message_type == "request_ai_move":
        await handle_ai_move_request(session, websocket, websocket_manager)
    
    elif message_type == "chat_message":
        await handle_chat_message(session_id, message, websocket_manager)


async def handle_make_move(session, message: dict, websocket: WebSocket, websocket_manager):
    """Handle move making via WebSocket"""
    move_data = message.get("data", {})
    from_pos = move_data.get("from")
    to_pos = move_data.get("to")
    promotion = move_data.get("promotion")
    
    if from_pos and to_pos:
        try:
            success = session.make_move(
                from_pos[0], from_pos[1], to_pos[0], to_pos[1],
                promotion.get("type") if promotion else None,
                promotion.get("piece") if promotion else None
            )
            
            if success:
                # Broadcast update to all connected players
                update_message = {
                    "type": "move_made",
                    "data": {
                        "from": from_pos,
                        "to": to_pos,
                        "promotion": promotion,
                        "success": True,
                        "game_state": session.get_game_state()
                    }
                }
                await websocket_manager.broadcast_to_session(session.session_id, update_message)
            else:
                error_message = {
                    "type": "error",
                    "data": {"message": "Invalid move"}
                }
                await websocket.send_json(error_message)
                
        except Exception as e:
            error_message = {
                "type": "error",
                "data": {"message": str(e)}
            }
            await websocket.send_json(error_message)


async def handle_ai_move_request(session, websocket: WebSocket, websocket_manager):
    """Handle AI move request via WebSocket"""
    if session.mode == GameMode.HUMAN_VS_AI:
        try:
            ai_move = session.get_ai_move()
            if ai_move:
                # Make the AI move
                success = session.make_move(
                    ai_move['from'][0], ai_move['from'][1],
                    ai_move['to'][0], ai_move['to'][1],
                    ai_move.get('promotion')
                )
                
                if success:
                    update_message = {
                        "type": "ai_move_made",
                        "data": {
                            "move": ai_move,
                            "success": True,
                            "game_state": session.get_game_state()
                        }
                    }
                    await websocket_manager.broadcast_to_session(session.session_id, update_message)
                
        except Exception as e:
            error_message = {
                "type": "error",
                "data": {"message": f"AI move error: {str(e)}"}
            }
            await websocket.send_json(error_message)


async def handle_chat_message(session_id: str, message: dict, websocket_manager):
    """Handle chat messages via WebSocket"""
    chat_data = message.get("data", {})
    chat_message = {
        "type": "chat_message",
        "data": {
            "player": chat_data.get("player", "Unknown"),
            "message": chat_data.get("message", ""),
            "timestamp": time.time()
        }
    }
    await websocket_manager.broadcast_to_session(session_id, chat_message)
