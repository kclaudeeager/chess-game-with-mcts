"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import time


class PromotionData(BaseModel):
    type: str
    piece: str


class MakeMoveRequest(BaseModel):
    from_pos: List[int]
    to_pos: List[int]
    promotion: Optional[PromotionData] = None


class CreateSessionRequest(BaseModel):
    mode: str = 'human_vs_ai'
    use_rl_engine: bool = False
    difficulty: str = "medium"
    player_name: str = "Player"


class CreateInvitationRequest(BaseModel):
    host_name: str = "Host Player"
    use_rl_engine: bool = False


class JoinSessionRequest(BaseModel):
    player_name: str = "Guest Player"


class SessionInfoResponse(BaseModel):
    session_id: str
    success: bool
    game_state: Dict[str, Any]


class InvitationResponse(BaseModel):
    success: bool
    invitation_code: str
    host_name: str
    expires_at: str


class MoveResponse(BaseModel):
    success: bool
    board: dict
    legal_moves: List
    is_checkmate: bool
    is_stalemate: bool
    is_check: bool
    material_balance: dict
    game_result: str
    message: Optional[str] = None


class WebSocketMessage(BaseModel):
    type: str
    data: dict
    timestamp: float = time.time()
