"""
Chess board implementation with full chess rules and evaluation.
"""
import copy
import json
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


class Color(Enum):
    WHITE = "white"
    BLACK = "black"


class PieceType(Enum):
    PAWN = "P"
    ROOK = "R"
    KNIGHT = "N" 
    BISHOP = "B"
    QUEEN = "Q"
    KING = "K"


class GameMode(Enum):
    HUMAN_VS_AI = "human_vs_ai"
    HUMAN_VS_HUMAN = "human_vs_human"


class GameResult(Enum):
    IN_PROGRESS = "in_progress"
    WHITE_WINS = "white_wins"
    BLACK_WINS = "black_wins"
    DRAW = "draw"


@dataclass
class Piece:
    type: PieceType
    color: Color
    has_moved: bool = False
    
    def copy(self):
        return Piece(self.type, self.color, self.has_moved)


class ChessBoard:
    """Enhanced chess board with full rules implementation"""
    
    def __init__(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.current_player = Color.WHITE
        self.kings = {Color.WHITE: (7, 4), Color.BLACK: (0, 4)}
        self.castling_rights = {
            Color.WHITE: {"kingside": True, "queenside": True},
            Color.BLACK: {"kingside": True, "queenside": True}
        }
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history = []
        self.position_history = []
        self._setup_initial_position()
    
    def _setup_initial_position(self):
        """Set up the standard chess starting position"""
        # Place pawns
        for col in range(8):
            self.board[1][col] = Piece(PieceType.PAWN, Color.BLACK)
            self.board[6][col] = Piece(PieceType.PAWN, Color.WHITE)
        
        # Place other pieces
        piece_order = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, 
                      PieceType.QUEEN, PieceType.KING, PieceType.BISHOP, 
                      PieceType.KNIGHT, PieceType.ROOK]
        
        for col, piece_type in enumerate(piece_order):
            self.board[0][col] = Piece(piece_type, Color.BLACK)
            self.board[7][col] = Piece(piece_type, Color.WHITE)
    
    def copy(self):
        """Create a deep copy of the chess board"""
        new_board = ChessBoard()
        new_board.board = [[piece.copy() if piece else None for piece in row] for row in self.board]
        new_board.current_player = self.current_player
        new_board.kings = self.kings.copy()
        new_board.castling_rights = copy.deepcopy(self.castling_rights)
        new_board.en_passant_target = self.en_passant_target
        new_board.halfmove_clock = self.halfmove_clock
        new_board.fullmove_number = self.fullmove_number
        new_board.move_history = self.move_history.copy()
        new_board.position_history = self.position_history.copy()
        return new_board

    def get_piece_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all legal moves for a piece at the given position"""
        piece = self.board[row][col]
        if not piece or piece.color != self.current_player:
            return []
        
        # Get raw moves (without legality checks)
        moves = self._get_raw_piece_moves(row, col)
        
        # Add castling moves for kings
        if piece.type == PieceType.KING:
            moves.extend(self._get_castling_moves(row, col))
        
        # Filter out moves that would put own king in check
        legal_moves = []
        for to_row, to_col in moves:
            if self._is_legal_move(row, col, to_row, to_col):
                legal_moves.append((to_row, to_col))
        
        return legal_moves
    
    def get_all_legal_moves(self) -> List[Tuple[int, int, int, int]]:
        """Get all legal moves for the current player"""
        legal_moves = []
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == self.current_player:
                    piece_moves = self.get_piece_moves(row, col)
                    for to_row, to_col in piece_moves:
                        legal_moves.append((row, col, to_row, to_col))
        
        return legal_moves
    
    def _get_raw_piece_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw moves for a piece (without checking for legality)"""
        piece = self.board[row][col]
        if not piece:
            return []
        
        if piece.type == PieceType.PAWN:
            return self._get_raw_pawn_moves(row, col)
        elif piece.type == PieceType.ROOK:
            return self._get_raw_rook_moves(row, col)
        elif piece.type == PieceType.KNIGHT:
            return self._get_raw_knight_moves(row, col)
        elif piece.type == PieceType.BISHOP:
            return self._get_raw_bishop_moves(row, col)
        elif piece.type == PieceType.QUEEN:
            return self._get_raw_queen_moves(row, col)
        elif piece.type == PieceType.KING:
            return self._get_raw_king_moves(row, col)
        
        return []
    
    def _get_raw_pawn_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw pawn moves"""
        piece = self.board[row][col]
        moves = []
        direction = -1 if piece.color == Color.WHITE else 1
        start_row = 6 if piece.color == Color.WHITE else 1
        
        # Forward moves
        new_row = row + direction
        if 0 <= new_row < 8 and not self.board[new_row][col]:
            moves.append((new_row, col))
            
            # Double move from starting position
            if row == start_row and not self.board[new_row + direction][col]:
                moves.append((new_row + direction, col))
        
        # Captures
        for dc in [-1, 1]:
            new_col = col + dc
            if 0 <= new_col < 8 and 0 <= new_row < 8:
                target = self.board[new_row][new_col]
                if target and target.color != piece.color:
                    moves.append((new_row, new_col))
                # En passant
                elif self.en_passant_target == (new_row, new_col):
                    moves.append((new_row, new_col))
        
        return moves
    
    def _get_raw_rook_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw rook moves"""
        return self._get_sliding_moves(row, col, [(0, 1), (0, -1), (1, 0), (-1, 0)])
    
    def _get_raw_bishop_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw bishop moves"""
        return self._get_sliding_moves(row, col, [(1, 1), (1, -1), (-1, 1), (-1, -1)])
    
    def _get_raw_queen_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw queen moves"""
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        return self._get_sliding_moves(row, col, directions)
    
    def _get_raw_knight_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw knight moves"""
        moves = []
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        
        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target = self.board[new_row][new_col]
                if not target or target.color != self.board[row][col].color:
                    moves.append((new_row, new_col))
        
        return moves
    
    def _get_raw_king_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get raw king moves (basic moves only, no castling to avoid recursion)"""
        moves = []
        
        # Only basic king moves (one square in any direction)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    target = self.board[new_row][new_col]
                    if not target or target.color != self.board[row][col].color:
                        moves.append((new_row, new_col))
        
        return moves
    
    def _get_castling_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get castling moves for the king (separate from raw moves to avoid recursion)"""
        moves = []
        piece = self.board[row][col]
        
        if piece.type != PieceType.KING or piece.has_moved:
            return moves
        
        # Kingside castling
        if self.castling_rights[piece.color]["kingside"]:
            if (not self.board[row][5] and not self.board[row][6] and
                self.board[row][7] and self.board[row][7].type == PieceType.ROOK and
                not self.board[row][7].has_moved):
                moves.append((row, 6))
        
        # Queenside castling
        if self.castling_rights[piece.color]["queenside"]:
            if (not self.board[row][1] and not self.board[row][2] and not self.board[row][3] and
                self.board[row][0] and self.board[row][0].type == PieceType.ROOK and
                not self.board[row][0].has_moved):
                moves.append((row, 2))
        
        return moves
    
    def _get_sliding_moves(self, row: int, col: int, directions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Get sliding piece moves (rook, bishop, queen)"""
        moves = []
        piece = self.board[row][col]
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            while 0 <= new_row < 8 and 0 <= new_col < 8:
                target = self.board[new_row][new_col]
                if not target:
                    moves.append((new_row, new_col))
                elif target.color != piece.color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
                new_row, new_col = new_row + dr, new_col + dc
        
        return moves
    
    def _is_legal_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Check if a move is legal (doesn't leave king in check)"""
        piece = self.board[from_row][from_col]
        
        # Special validation for castling moves
        if piece and piece.type == PieceType.KING and abs(to_col - from_col) == 2:
            # This is a castling move - need special validation
            # King can't be in check when castling
            if self.is_in_check(piece.color):
                return False
            
            # Check if squares king passes through are safe
            start_col = from_col
            end_col = to_col
            step = 1 if end_col > start_col else -1
            
            for col in range(start_col + step, end_col + step, step):
                if self._is_square_attacked(from_row, col, piece.color):
                    return False
        
        # Make a copy and try the move
        temp_board = self.copy()
        if temp_board._make_move_unchecked(from_row, from_col, to_row, to_col):
            return not temp_board.is_in_check(self.current_player)
        return False
    
    def _make_move_unchecked(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Make a move without checking for legality"""
        piece = self.board[from_row][from_col]
        if not piece:
            return False
        
        # Handle special moves
        if piece.type == PieceType.KING and abs(to_col - from_col) == 2:
            # Castling
            rook_col = 7 if to_col > from_col else 0
            rook_new_col = 5 if to_col > from_col else 3
            rook = self.board[from_row][rook_col]
            self.board[from_row][rook_new_col] = rook
            self.board[from_row][rook_col] = None
            if rook:
                rook.has_moved = True
        
        elif piece.type == PieceType.PAWN and self.en_passant_target == (to_row, to_col):
            # En passant capture
            captured_pawn_row = to_row + (1 if piece.color == Color.WHITE else -1)
            self.board[captured_pawn_row][to_col] = None
        
        # Make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        piece.has_moved = True
        
        # Update king position
        if piece.type == PieceType.KING:
            self.kings[piece.color] = (to_row, to_col)
        
        return True
    
    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int, 
                  special_move_type=None, promotion_piece=None) -> bool:
        """Make a move with full validation and game state updates"""
        if not self._is_legal_move(from_row, from_col, to_row, to_col):
            return False
        
        piece = self.board[from_row][from_col]
        captured_piece = self.board[to_row][to_col]
        
        # Update en passant target
        old_en_passant = self.en_passant_target
        self.en_passant_target = None
        
        if piece.type == PieceType.PAWN and abs(to_row - from_row) == 2:
            self.en_passant_target = ((from_row + to_row) // 2, from_col)
        
        # Make the move
        success = self._make_move_unchecked(from_row, from_col, to_row, to_col)
        if not success:
            return False
        
        # Handle pawn promotion
        if piece.type == PieceType.PAWN and (to_row == 0 or to_row == 7):
            promotion_type = PieceType.QUEEN  # Default to queen
            if promotion_piece:
                promotion_map = {
                    'Q': PieceType.QUEEN, 'R': PieceType.ROOK,
                    'B': PieceType.BISHOP, 'N': PieceType.KNIGHT
                }
                promotion_type = promotion_map.get(promotion_piece.upper(), PieceType.QUEEN)
            self.board[to_row][to_col] = Piece(promotion_type, piece.color, True)
        
        # Update castling rights
        if piece.type == PieceType.KING:
            self.castling_rights[piece.color]["kingside"] = False
            self.castling_rights[piece.color]["queenside"] = False
        elif piece.type == PieceType.ROOK:
            if from_row == 0 or from_row == 7:
                if from_col == 0:
                    self.castling_rights[piece.color]["queenside"] = False
                elif from_col == 7:
                    self.castling_rights[piece.color]["kingside"] = False
        
        # Update move counters
        if piece.type == PieceType.PAWN or captured_piece:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        if self.current_player == Color.BLACK:
            self.fullmove_number += 1
        
        # Record move
        move_notation = f"{chr(97 + from_col)}{8 - from_row}{chr(97 + to_col)}{8 - to_row}"
        self.move_history.append(move_notation)
        self.position_history.append(self._get_position_key())
        
        # Switch players
        self.current_player = Color.BLACK if self.current_player == Color.WHITE else Color.WHITE
        
        return True
    
    def is_in_check(self, color: Color) -> bool:
        """Check if the king of the given color is in check"""
        king_pos = self.kings[color]
        opponent_color = Color.BLACK if color == Color.WHITE else Color.WHITE
        
        # Check if any opponent piece can attack the king using raw moves
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == opponent_color:
                    # Use raw moves to avoid recursion
                    moves = self._get_raw_piece_moves(row, col)
                    if king_pos in moves:
                        return True
        return False
    
    def _is_square_attacked(self, row: int, col: int, defending_color: Color) -> bool:
        """Check if a square is attacked by the opponent"""
        attacking_color = Color.BLACK if defending_color == Color.WHITE else Color.WHITE
        
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.color == attacking_color:
                    # Use raw moves to avoid recursion
                    raw_moves = self._get_raw_piece_moves(r, c)
                    if (row, col) in raw_moves:
                        return True
        return False
    
    def is_checkmate(self) -> bool:
        """Check if current player is in checkmate"""
        if not self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def is_stalemate(self) -> bool:
        """Check if current player is in stalemate"""
        if self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def is_draw_by_fifty_moves(self) -> bool:
        """Check for draw by 50-move rule"""
        return self.halfmove_clock >= 100
    
    def is_insufficient_material(self) -> bool:
        """Check for insufficient material to checkmate"""
        white_pieces = []
        black_pieces = []
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.type != PieceType.KING:
                    if piece.color == Color.WHITE:
                        white_pieces.append((piece.type, row, col))
                    else:
                        black_pieces.append((piece.type, row, col))
        
        # King vs King
        if len(white_pieces) == 0 and len(black_pieces) == 0:
            return True
        
        # King and minor piece vs King
        if ((len(white_pieces) == 1 and len(black_pieces) == 0 and 
             white_pieces[0][0] in [PieceType.BISHOP, PieceType.KNIGHT]) or
            (len(black_pieces) == 1 and len(white_pieces) == 0 and 
             black_pieces[0][0] in [PieceType.BISHOP, PieceType.KNIGHT])):
            return True
        
        return False
    
    def is_threefold_repetition(self) -> bool:
        """Check for threefold repetition"""
        if len(self.position_history) < 8:
            return False
        
        current_position = self._get_position_key()
        count = self.position_history.count(current_position)
        return count >= 2  # Current position + 2 previous = 3 total
    
    def _get_position_key(self) -> str:
        """Get a position key for repetition detection"""
        position_str = ""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    position_str += f"{piece.color.value[0]}{piece.type.value}"
                else:
                    position_str += "."
        
        position_str += f"{self.current_player.value}"
        position_str += str(self.castling_rights)
        position_str += str(self.en_passant_target)
        
        return position_str
    
    def get_game_result(self) -> GameResult:
        """Determine the current game result"""
        if self.is_checkmate():
            return GameResult.BLACK_WINS if self.current_player == Color.WHITE else GameResult.WHITE_WINS
        
        if (self.is_stalemate() or self.is_draw_by_fifty_moves() or 
            self.is_insufficient_material() or self.is_threefold_repetition()):
            return GameResult.DRAW
        
        return GameResult.IN_PROGRESS
    
    def calculate_material_balance(self) -> Dict:
        """Calculate material balance for both sides"""
        piece_values = {
            PieceType.PAWN: 1, PieceType.KNIGHT: 3, PieceType.BISHOP: 3,
            PieceType.ROOK: 5, PieceType.QUEEN: 9, PieceType.KING: 0
        }
        
        white_material = 0
        black_material = 0
        white_pieces = []
        black_pieces = []
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    value = piece_values[piece.type]
                    if piece.color == Color.WHITE:
                        white_material += value
                        white_pieces.append(piece.type.value)
                    else:
                        black_material += value
                        black_pieces.append(piece.type.value)
        
        return {
            'white_material': white_material,
            'black_material': black_material,
            'material_balance': white_material - black_material,
            'white_pieces': white_pieces,
            'black_pieces': black_pieces
        }
    
    def to_dict(self) -> Dict:
        """Convert board to dictionary for JSON serialization"""
        board_dict = []
        for row in range(8):
            row_dict = []
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    row_dict.append({
                        'type': piece.type.value,
                        'color': piece.color.value,
                        'has_moved': piece.has_moved
                    })
                else:
                    row_dict.append(None)
            board_dict.append(row_dict)
        
        material_info = self.calculate_material_balance()
        game_result = self.get_game_result()
        
        return {
            'board': board_dict,
            'current_player': self.current_player.value,
            'move_history': self.move_history,
            'kings': {color.value: pos for color, pos in self.kings.items()},
            'material_balance': material_info,
            'game_result': game_result.value,
            'is_check': self.is_in_check(self.current_player),
            'is_checkmate': self.is_checkmate(),
            'is_stalemate': self.is_stalemate(),
            'is_draw': game_result == GameResult.DRAW,
            'castling_rights': {
                color.value: rights for color, rights in self.castling_rights.items()
            },
            'en_passant_target': self.en_passant_target,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number
        }
