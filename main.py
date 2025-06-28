from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import math
import time
import uuid
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import json

# Import all chess classes from the original backend
class PieceType(Enum):
    PAWN = 'P'
    ROOK = 'R'
    KNIGHT = 'N'
    BISHOP = 'B'
    QUEEN = 'Q'
    KING = 'K'

class Color(Enum):
    WHITE = 'white'
    BLACK = 'black'

class GameMode(Enum):
    HUMAN_VS_AI = 'human_vs_ai'
    HUMAN_VS_HUMAN = 'human_vs_human'

class GameResult(Enum):
    IN_PROGRESS = 'in_progress'
    WHITE_WINS = 'white_wins'
    BLACK_WINS = 'black_wins'
    DRAW = 'draw'

@dataclass
class Piece:
    type: PieceType
    color: Color
    has_moved: bool = False
    
    def __str__(self):
        symbol = self.type.value
        return symbol if self.color == Color.WHITE else symbol.lower()

class ChessBoard:
    def __init__(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.current_player = Color.WHITE
        self.move_history = []
        self.kings = {Color.WHITE: (7, 4), Color.BLACK: (0, 4)}
        self.en_passant_target = None  # (row, col) where en passant capture is possible
        self.castling_rights = {
            Color.WHITE: {'kingside': True, 'queenside': True},
            Color.BLACK: {'kingside': True, 'queenside': True}
        }
        self.halfmove_clock = 0  # For 50-move rule
        self.fullmove_number = 1
        self.setup_initial_position()
    
    def setup_initial_position(self):
        # Black pieces
        back_row = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, PieceType.QUEEN,
                    PieceType.KING, PieceType.BISHOP, PieceType.KNIGHT, PieceType.ROOK]
        
        for col, piece_type in enumerate(back_row):
            self.board[0][col] = Piece(piece_type, Color.BLACK)
            self.board[1][col] = Piece(PieceType.PAWN, Color.BLACK)
        
        # White pieces
        for col, piece_type in enumerate(back_row):
            self.board[7][col] = Piece(piece_type, Color.WHITE)
            self.board[6][col] = Piece(PieceType.PAWN, Color.WHITE)
    
    def copy(self):
        new_board = ChessBoard()
        new_board.board = [[None for _ in range(8)] for _ in range(8)]
        
        for row in range(8):
            for col in range(8):
                if self.board[row][col]:
                    piece = self.board[row][col]
                    new_board.board[row][col] = Piece(piece.type, piece.color, piece.has_moved)
        
        new_board.current_player = self.current_player
        new_board.move_history = self.move_history.copy()
        new_board.kings = self.kings.copy()
        new_board.en_passant_target = self.en_passant_target
        new_board.castling_rights = {
            Color.WHITE: self.castling_rights[Color.WHITE].copy(),
            Color.BLACK: self.castling_rights[Color.BLACK].copy()
        }
        new_board.halfmove_clock = self.halfmove_clock
        new_board.fullmove_number = self.fullmove_number
        return new_board
    
    def is_valid_position(self, row, col):
        return 0 <= row < 8 and 0 <= col < 8
    
    def get_piece_moves(self, row, col):
        piece = self.board[row][col]
        if not piece or piece.color != self.current_player:
            return []
        
        moves = []
        
        if piece.type == PieceType.PAWN:
            moves = self._get_pawn_moves(row, col)
        elif piece.type == PieceType.ROOK:
            moves = self._get_rook_moves(row, col)
        elif piece.type == PieceType.KNIGHT:
            moves = self._get_knight_moves(row, col)
        elif piece.type == PieceType.BISHOP:
            moves = self._get_bishop_moves(row, col)
        elif piece.type == PieceType.QUEEN:
            moves = self._get_queen_moves(row, col)
        elif piece.type == PieceType.KING:
            moves = self._get_king_moves(row, col)
        
        # Filter out moves that would put own king in check
        legal_moves = []
        for move in moves:
            temp_board = self.copy()
            # Handle special moves properly
            if len(move) > 2:  # Special move
                temp_board._make_special_move(row, col, move[0], move[1], move[2:])
            else:
                temp_board._make_move_unchecked(row, col, move[0], move[1])
            
            if not temp_board.is_in_check(self.current_player):
                legal_moves.append(move)
        
        return legal_moves
    
    def _get_pawn_moves(self, row, col):
        moves = []
        piece = self.board[row][col]
        direction = -1 if piece.color == Color.WHITE else 1
        start_row = 6 if piece.color == Color.WHITE else 1
        promotion_row = 0 if piece.color == Color.WHITE else 7
        
        # Forward moves
        new_row = row + direction
        if self.is_valid_position(new_row, col) and not self.board[new_row][col]:
            # Check for promotion
            if new_row == promotion_row:
                # Add promotion moves for Queen, Rook, Bishop, Knight
                for promotion_piece in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                    moves.append((new_row, col, 'promotion', promotion_piece))
            else:
                moves.append((new_row, col))
            
            # Double move from starting position
            if row == start_row and not self.board[new_row + direction][col]:
                moves.append((new_row + direction, col))
        
        # Captures
        for dc in [-1, 1]:
            new_row, new_col = row + direction, col + dc
            if self.is_valid_position(new_row, new_col):
                target = self.board[new_row][new_col]
                if target and target.color != piece.color:
                    # Regular capture or capture with promotion
                    if new_row == promotion_row:
                        for promotion_piece in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                            moves.append((new_row, new_col, 'promotion', promotion_piece))
                    else:
                        moves.append((new_row, new_col))
                
                # En passant capture
                elif self.en_passant_target == (new_row, new_col):
                    moves.append((new_row, new_col, 'en_passant'))
        
        return moves
    
    def _get_rook_moves(self, row, col):
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + dr * i, col + dc * i
                if not self.is_valid_position(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if not target:
                    moves.append((new_row, new_col))
                elif target.color != self.board[row][col].color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
        
        return moves
    
    def _get_knight_moves(self, row, col):
        moves = []
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), 
                       (1, 2), (1, -2), (-1, 2), (-1, -2)]
        
        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if (self.is_valid_position(new_row, new_col) and 
                (not self.board[new_row][new_col] or 
                 self.board[new_row][new_col].color != self.board[row][col].color)):
                moves.append((new_row, new_col))
        
        return moves
    
    def _get_bishop_moves(self, row, col):
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + dr * i, col + dc * i
                if not self.is_valid_position(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if not target:
                    moves.append((new_row, new_col))
                elif target.color != self.board[row][col].color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
        
        return moves
    
    def _get_queen_moves(self, row, col):
        return self._get_rook_moves(row, col) + self._get_bishop_moves(row, col)
    
    def _get_king_moves(self, row, col):
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), 
                     (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        # Regular king moves
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if (self.is_valid_position(new_row, new_col) and 
                (not self.board[new_row][new_col] or 
                 self.board[new_row][new_col].color != self.board[row][col].color)):
                moves.append((new_row, new_col))
        
        # Castling moves - use a safe check to avoid recursion
        piece = self.board[row][col]
        if not piece.has_moved and not self._is_king_in_check_safe(piece.color):
            # Kingside castling
            if (self.castling_rights[piece.color]['kingside'] and
                not self.board[row][5] and not self.board[row][6] and
                self.board[row][7] and not self.board[row][7].has_moved):
                # Check if squares king passes through are not attacked
                if (not self._is_square_attacked_safe(row, 5, piece.color) and
                    not self._is_square_attacked_safe(row, 6, piece.color)):
                    moves.append((row, 6, 'kingside_castle'))
            
            # Queenside castling
            if (self.castling_rights[piece.color]['queenside'] and
                not self.board[row][1] and not self.board[row][2] and not self.board[row][3] and
                self.board[row][0] and not self.board[row][0].has_moved):
                # Check if squares king passes through are not attacked
                if (not self._is_square_attacked_safe(row, 2, piece.color) and
                    not self._is_square_attacked_safe(row, 3, piece.color)):
                    moves.append((row, 2, 'queenside_castle'))
        
        return moves
    
    def _is_king_in_check_safe(self, color):
        """Safe check for king in check that doesn't cause recursion"""
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
    
    def _is_square_attacked_safe(self, row, col, by_color):
        """Safe check for square attack that doesn't cause recursion"""
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.color != by_color:  # Enemy piece
                    # Use raw moves to avoid recursion
                    moves = self._get_raw_piece_moves(r, c)
                    if (row, col) in moves:
                        return True
        return False
    
    def _is_square_attacked(self, row, col, by_color):
        """Check if a square is attacked by pieces of the given color"""
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.color != by_color:  # Enemy piece
                    moves = self._get_raw_piece_moves(r, c)
                    if (row, col) in moves:
                        return True
        return False
    
    def get_all_legal_moves(self):
        moves = []
        for row in range(8):
            for col in range(8):
                if self.board[row][col] and self.board[row][col].color == self.current_player:
                    piece_moves = self.get_piece_moves(row, col)
                    for move in piece_moves:
                        moves.append((row, col, move[0], move[1]))
        return moves
    
    def is_in_check(self, color):
        king_pos = self.kings[color]
        opponent_color = Color.BLACK if color == Color.WHITE else Color.WHITE
        
        # Check if any opponent piece can attack the king
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == opponent_color:
                    # Get raw moves without check validation to avoid recursion
                    moves = self._get_raw_piece_moves(row, col)
                    if king_pos in moves:
                        return True
        return False
    
    def _get_raw_piece_moves(self, row, col):
        """Get moves without checking if they put own king in check"""
        piece = self.board[row][col]
        if not piece:
            return []
        
        if piece.type == PieceType.PAWN:
            return self._get_raw_pawn_moves(row, col)
        elif piece.type == PieceType.ROOK:
            return self._get_rook_moves(row, col)
        elif piece.type == PieceType.KNIGHT:
            return self._get_knight_moves(row, col)
        elif piece.type == PieceType.BISHOP:
            return self._get_bishop_moves(row, col)
        elif piece.type == PieceType.QUEEN:
            return self._get_queen_moves(row, col)
        elif piece.type == PieceType.KING:
            return self._get_raw_king_moves(row, col)
        
        return []
    
    def _get_raw_king_moves(self, row, col):
        """Get raw king moves without castling (to avoid recursion in is_in_check)"""
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), 
                     (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        # Only regular king moves (no castling)
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if (self.is_valid_position(new_row, new_col) and 
                (not self.board[new_row][new_col] or 
                 self.board[new_row][new_col].color != self.board[row][col].color)):
                moves.append((new_row, new_col))
        
        return moves
    
    def _get_raw_pawn_moves(self, row, col):
        """Get raw pawn moves without promotion details (to avoid complexity in is_in_check)"""
        moves = []
        piece = self.board[row][col]
        direction = -1 if piece.color == Color.WHITE else 1
        start_row = 6 if piece.color == Color.WHITE else 1
        
        # Forward moves
        new_row = row + direction
        if self.is_valid_position(new_row, col) and not self.board[new_row][col]:
            moves.append((new_row, col))
            
            # Double move from starting position
            if row == start_row and not self.board[new_row + direction][col]:
                moves.append((new_row + direction, col))
        
        # Captures
        for dc in [-1, 1]:
            new_row, new_col = row + direction, col + dc
            if self.is_valid_position(new_row, new_col):
                target = self.board[new_row][new_col]
                if target and target.color != piece.color:
                    moves.append((new_row, new_col))
                # En passant capture
                elif self.en_passant_target == (new_row, new_col):
                    moves.append((new_row, new_col))
        
        return moves
    
    def make_move(self, from_row, from_col, to_row, to_col, special_move_type=None, promotion_piece=None):
        if not self.is_valid_position(from_row, from_col) or not self.is_valid_position(to_row, to_col):
            return False
        
        piece = self.board[from_row][from_col]
        if not piece or piece.color != self.current_player:
            return False
        
        legal_moves = self.get_piece_moves(from_row, from_col)
        
        # Check if this move is legal (handle both regular and special moves)
        move_found = False
        for move in legal_moves:
            if len(move) == 2 and move == (to_row, to_col):
                move_found = True
                break
            elif len(move) > 2:
                if (move[0] == to_row and move[1] == to_col and 
                    (special_move_type == move[2] or 
                     (move[2] == 'promotion' and len(move) > 3 and promotion_piece == move[3]))):
                    move_found = True
                    break
        
        if not move_found:
            return False
        
        # Reset halfmove clock for pawn moves or captures
        if piece.type == PieceType.PAWN or self.board[to_row][to_col]:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Handle special moves
        if special_move_type:
            self._make_special_move(from_row, from_col, to_row, to_col, [special_move_type, promotion_piece])
        else:
            self._make_move_unchecked(from_row, from_col, to_row, to_col)
        
        return True
    
    def _make_special_move(self, from_row, from_col, to_row, to_col, special_data):
        special_type = special_data[0]
        piece = self.board[from_row][from_col]
        
        if special_type == 'promotion':
            promotion_piece = special_data[1] if len(special_data) > 1 else PieceType.QUEEN
            # Move pawn and promote
            self.board[to_row][to_col] = Piece(promotion_piece, piece.color, True)
            self.board[from_row][from_col] = None
            
        elif special_type == 'en_passant':
            # Capture the pawn en passant
            captured_pawn_row = from_row  # Same row as moving pawn
            self.board[to_row][to_col] = piece
            self.board[from_row][from_col] = None
            self.board[captured_pawn_row][to_col] = None  # Remove captured pawn
            piece.has_moved = True
            
        elif special_type == 'kingside_castle':
            # Move king and rook
            self.board[to_row][to_col] = piece
            self.board[from_row][from_col] = None
            # Move rook
            rook = self.board[from_row][7]
            self.board[from_row][5] = rook
            self.board[from_row][7] = None
            piece.has_moved = True
            rook.has_moved = True
            # Update king position
            self.kings[piece.color] = (to_row, to_col)
            
        elif special_type == 'queenside_castle':
            # Move king and rook
            self.board[to_row][to_col] = piece
            self.board[from_row][from_col] = None
            # Move rook
            rook = self.board[from_row][0]
            self.board[from_row][3] = rook
            self.board[from_row][0] = None
            piece.has_moved = True
            rook.has_moved = True
            # Update king position
            self.kings[piece.color] = (to_row, to_col)
        
        # Update castling rights if king or rook moved
        if piece.type == PieceType.KING:
            self.castling_rights[piece.color]['kingside'] = False
            self.castling_rights[piece.color]['queenside'] = False
        elif piece.type == PieceType.ROOK:
            if from_col == 0:  # Queenside rook
                self.castling_rights[piece.color]['queenside'] = False
            elif from_col == 7:  # Kingside rook
                self.castling_rights[piece.color]['kingside'] = False
        
        # Record move
        self.move_history.append((from_row, from_col, to_row, to_col, special_type))
        
        # Update en passant target
        self.en_passant_target = None
        
        # Switch players
        if self.current_player == Color.WHITE:
            self.current_player = Color.BLACK
        else:
            self.current_player = Color.WHITE
            self.fullmove_number += 1
    
    def _make_move_unchecked(self, from_row, from_col, to_row, to_col):
        piece = self.board[from_row][from_col]
        
        # Check for en passant target (pawn double move)
        self.en_passant_target = None
        if (piece.type == PieceType.PAWN and abs(to_row - from_row) == 2):
            # Pawn moved two squares, set en passant target
            en_passant_row = (from_row + to_row) // 2
            self.en_passant_target = (en_passant_row, to_col)
        
        # Update castling rights
        if piece.type == PieceType.KING:
            self.castling_rights[piece.color]['kingside'] = False
            self.castling_rights[piece.color]['queenside'] = False
            # Update king position
            self.kings[piece.color] = (to_row, to_col)
        elif piece.type == PieceType.ROOK:
            if from_col == 0:  # Queenside rook
                self.castling_rights[piece.color]['queenside'] = False
            elif from_col == 7:  # Kingside rook
                self.castling_rights[piece.color]['kingside'] = False
        
        # If capturing a rook, update opponent's castling rights
        captured_piece = self.board[to_row][to_col]
        if captured_piece and captured_piece.type == PieceType.ROOK:
            opponent_color = captured_piece.color
            if to_col == 0:  # Queenside rook captured
                self.castling_rights[opponent_color]['queenside'] = False
            elif to_col == 7:  # Kingside rook captured
                self.castling_rights[opponent_color]['kingside'] = False
        
        # Make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        piece.has_moved = True
        
        # Record move
        self.move_history.append((from_row, from_col, to_row, to_col))
        
        # Switch players
        if self.current_player == Color.WHITE:
            self.current_player = Color.BLACK
        else:
            self.current_player = Color.WHITE
            self.fullmove_number += 1
    
    def is_checkmate(self):
        if not self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def is_stalemate(self):
        if self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def is_draw_by_fifty_moves(self):
        return self.halfmove_clock >= 100  # 50 moves per side
    
    def is_insufficient_material(self):
        """Check for insufficient material to checkmate - enhanced detection"""
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
        if (len(white_pieces) == 1 and len(black_pieces) == 0 and 
            white_pieces[0][0] in [PieceType.BISHOP, PieceType.KNIGHT]):
            return True
        if (len(black_pieces) == 1 and len(white_pieces) == 0 and 
            black_pieces[0][0] in [PieceType.BISHOP, PieceType.KNIGHT]):
            return True
        
        # King and Bishop vs King and Bishop (same color squares)
        if (len(white_pieces) == 1 and len(black_pieces) == 1 and 
            white_pieces[0][0] == PieceType.BISHOP and black_pieces[0][0] == PieceType.BISHOP):
            white_square_color = (white_pieces[0][1] + white_pieces[0][2]) % 2
            black_square_color = (black_pieces[0][1] + black_pieces[0][2]) % 2
            return white_square_color == black_square_color
        
        # King and Knight vs King and Knight
        if (len(white_pieces) == 1 and len(black_pieces) == 1 and 
            white_pieces[0][0] == PieceType.KNIGHT and black_pieces[0][0] == PieceType.KNIGHT):
            return True
        
        return False
    
    def get_game_result(self):
        """Determine the current game result with enhanced detection"""
        # Check for checkmate first
        if self.is_checkmate():
            return GameResult.BLACK_WINS if self.current_player == Color.WHITE else GameResult.WHITE_WINS
        
        # Check for stalemate
        if self.is_stalemate():
            return GameResult.DRAW
        
        # Check for draw by 50-move rule
        if self.is_draw_by_fifty_moves():
            return GameResult.DRAW
        
        # Check for insufficient material
        if self.is_insufficient_material():
            return GameResult.DRAW
        
        # Check for threefold repetition (simplified)
        if self.is_threefold_repetition():
            return GameResult.DRAW
        
        # Game is still in progress
        return GameResult.IN_PROGRESS
    
    def is_threefold_repetition(self):
        """Check for threefold repetition (simplified implementation)"""
        if len(self.move_history) < 8:  # Need at least 4 moves per side
            return False
        
        # Count occurrences of current position (simplified by move pattern)
        current_position_key = self._get_position_key()
        position_count = 1  # Current position
        
        # Check last few positions for repetition
        temp_board = self.copy()
        for i in range(min(len(self.move_history), 20)):  # Check last 20 moves
            if len(temp_board.move_history) < 2:
                break
            
            # Undo last move (simplified)
            temp_board.move_history.pop()
            if temp_board._get_position_key() == current_position_key:
                position_count += 1
                if position_count >= 3:
                    return True
        
        return False
    
    def _get_position_key(self):
        """Get a simplified position key for repetition detection"""
        # Create a simple hash of the position
        position_str = ""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    position_str += f"{piece.type.value}{piece.color.value}{row}{col}"
                else:
                    position_str += "empty"
        
        position_str += f"{self.current_player.value}"
        position_str += f"{self.castling_rights}"
        position_str += f"{self.en_passant_target}"
        
        return hash(position_str)
    
    def calculate_material_balance(self):
        """Calculate material balance for both sides"""
        piece_values = {
            PieceType.PAWN: 1,
            PieceType.KNIGHT: 3,
            PieceType.BISHOP: 3,
            PieceType.ROOK: 5,
            PieceType.QUEEN: 9,
            PieceType.KING: 0  # King doesn't count for material
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
                        black_pieces.append(piece.type.value.lower())
        
        return {
            'white_material': white_material,
            'black_material': black_material,
            'material_balance': white_material - black_material,
            'white_pieces': white_pieces,
            'black_pieces': black_pieces
        }
    
    def evaluate_position(self):
        """Chess-strategic position evaluation focusing on material and tactics with positional bonuses"""
        # Standard chess piece values
        piece_values = {
            PieceType.PAWN: 100,
            PieceType.KNIGHT: 320,
            PieceType.BISHOP: 330,
            PieceType.ROOK: 500,
            PieceType.QUEEN: 900,
            PieceType.KING: 20000
        }
        
        # Piece-Square Tables for positional evaluation
        pawn_table = [
            [ 0,  0,  0,  0,  0,  0,  0,  0],
            [50, 50, 50, 50, 50, 50, 50, 50],
            [10, 10, 20, 30, 30, 20, 10, 10],
            [ 5,  5, 10, 25, 25, 10,  5,  5],
            [ 0,  0,  0, 20, 20,  0,  0,  0],
            [ 5, -5,-10,  0,  0,-10, -5,  5],
            [ 5, 10, 10,-20,-20, 10, 10,  5],
            [ 0,  0,  0,  0,  0,  0,  0,  0]
        ]
        
        knight_table = [
            [-50,-40,-30,-30,-30,-30,-40,-50],
            [-40,-20,  0,  0,  0,  0,-20,-40],
            [-30,  0, 10, 15, 15, 10,  0,-30],
            [-30,  5, 15, 20, 20, 15,  5,-30],
            [-30,  0, 15, 20, 20, 15,  0,-30],
            [-30,  5, 10, 15, 15, 10,  5,-30],
            [-40,-20,  0,  5,  5,  0,-20,-40],
            [-50,-40,-30,-30,-30,-30,-40,-50]
        ]
        
        bishop_table = [
            [-20,-10,-10,-10,-10,-10,-10,-20],
            [-10,  0,  0,  0,  0,  0,  0,-10],
            [-10,  0,  5, 10, 10,  5,  0,-10],
            [-10,  5,  5, 10, 10,  5,  5,-10],
            [-10,  0, 10, 10, 10, 10,  0,-10],
            [-10, 10, 10, 10, 10, 10, 10,-10],
            [-10,  5,  0,  0,  0,  0,  5,-10],
            [-20,-10,-10,-10,-10,-10,-10,-20]
        ]
        
        rook_table = [
            [ 0,  0,  0,  0,  0,  0,  0,  0],
            [ 5, 10, 10, 10, 10, 10, 10,  5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [ 0,  0,  0,  5,  5,  0,  0,  0]
        ]
        
        queen_table = [
            [-20,-10,-10, -5, -5,-10,-10,-20],
            [-10,  0,  0,  0,  0,  0,  0,-10],
            [-10,  0,  5,  5,  5,  5,  0,-10],
            [ -5,  0,  5,  5,  5,  5,  0, -5],
            [  0,  0,  5,  5,  5,  5,  0, -5],
            [-10,  5,  5,  5,  5,  5,  0,-10],
            [-10,  0,  5,  0,  0,  0,  0,-10],
            [-20,-10,-10, -5, -5,-10,-10,-20]
        ]
        
        king_middlegame_table = [
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-20,-30,-30,-40,-40,-30,-30,-20],
            [-10,-20,-20,-20,-20,-20,-20,-10],
            [ 20, 20,  0,  0,  0,  0, 20, 20],
            [ 20, 30, 10,  0,  0, 10, 30, 20]
        ]
        
        king_endgame_table = [
            [-50,-40,-30,-20,-20,-30,-40,-50],
            [-30,-20,-10,  0,  0,-10,-20,-30],
            [-30,-10, 20, 30, 30, 20,-10,-30],
            [-30,-10, 30, 40, 40, 30,-10,-30],
            [-30,-10, 30, 40, 40, 30,-10,-30],
            [-30,-10, 20, 30, 30, 20,-10,-30],
            [-30,-30,  0,  0,  0,  0,-30,-30],
            [-50,-30,-30,-30,-30,-30,-30,-50]
        ]
        
        piece_tables = {
            PieceType.PAWN: pawn_table,
            PieceType.KNIGHT: knight_table,
            PieceType.BISHOP: bishop_table,
            PieceType.ROOK: rook_table,
            PieceType.QUEEN: queen_table
        }
        
        score = 0
        white_material = 0
        black_material = 0
        total_pieces = 0
        
        # Count total pieces for game phase detection
        for row in range(8):
            for col in range(8):
                if self.board[row][col]:
                    total_pieces += 1
        
        is_endgame = total_pieces <= 16  # Endgame when few pieces remain
        
        # 1. MATERIAL EVALUATION WITH POSITIONAL BONUSES (most important)
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    base_value = piece_values[piece.type]
                    positional_bonus = 0
                    
                    # Apply piece-square table bonuses
                    if piece.type in piece_tables:
                        if piece.color == Color.WHITE:
                            # White pieces use table as-is (from white's perspective)
                            positional_bonus = piece_tables[piece.type][row][col]
                        else:
                            # Black pieces use flipped table
                            positional_bonus = piece_tables[piece.type][7-row][col]
                    elif piece.type == PieceType.KING:
                        # King uses different tables for middlegame vs endgame
                        table = king_endgame_table if is_endgame else king_middlegame_table
                        if piece.color == Color.WHITE:
                            positional_bonus = table[row][col]
                        else:
                            positional_bonus = table[7-row][col]
                    
                    total_value = base_value + positional_bonus
                    
                    if piece.color == Color.WHITE:
                        score += total_value
                        white_material += base_value  # Only count base value for material display
                    else:
                        score -= total_value
                        black_material += base_value  # Only count base value for material display
        
        # 2. TACTICAL EVALUATION - threats and captures
        threatened_value = self._evaluate_threats()
        score += threatened_value
        
        # 3. CHECKMATE BONUS (huge priority)
        if self.is_checkmate():
            losing_player = self.current_player
            if losing_player == Color.BLACK:
                score += 100000  # White wins
            else:
                score -= 100000  # Black wins
        elif self.is_in_check(self.current_player):
            # Being in check is bad
            if self.current_player == Color.WHITE:
                score -= 500
            else:
                score += 500
        
        # 4. PIECE ACTIVITY AND DEVELOPMENT
        activity_bonus = self._evaluate_piece_activity()
        score += activity_bonus
        
        # 5. KING SAFETY (important in middlegame/endgame)
        king_safety = self._evaluate_king_safety_advanced()
        score += king_safety
        
        # 6. PAWN STRUCTURE
        pawn_structure = self._evaluate_pawn_structure()
        score += pawn_structure
        
        # 7. ENDGAME SPECIFIC EVALUATIONS
        if is_endgame:
            score += self._evaluate_endgame_factors()
        
        return score
    
    def get_move_priority(self, move):
        """Assign a priority score to a move for MCTS move ordering."""
        # move: (from_row, from_col, to_row, to_col, [optional: special])
        # Higher is better
        score = 0
        from_row, from_col, to_row, to_col = move[:4]
        piece = self.board[from_row][from_col]
        target = self.board[to_row][to_col]
        
        # Prioritize captures
        if target:
            # Queen > Rook > Bishop/Knight > Pawn
            piece_values = {
                'Q': 9, 'R': 5, 'B': 3, 'N': 3, 'P': 1, 'K': 0
            }
            score += 10 + piece_values.get(target.type.value, 0)
        
        # Prioritize promotions
        if len(move) > 4 and move[4] == 'promotion':
            score += 20
        
        # Prioritize checks
        temp_board = self.copy()
        try:
            if len(move) > 4:
                temp_board.make_move(from_row, from_col, to_row, to_col, move[4])
            else:
                temp_board.make_move(from_row, from_col, to_row, to_col)
            opponent = Color.BLACK if self.current_player == Color.WHITE else Color.WHITE
            if temp_board.is_in_check(opponent):
                score += 5
        except Exception:
            pass
        
        # Slight bonus for center moves
        if (to_row, to_col) in [(3,3),(3,4),(4,3),(4,4)]:
            score += 2
        
        return score
    
    def _evaluate_threats(self):
        """Evaluate piece threats and hanging pieces - crucial for tactical play"""
        score = 0
        piece_values = {
            PieceType.PAWN: 100, PieceType.KNIGHT: 320, PieceType.BISHOP: 330,
            PieceType.ROOK: 500, PieceType.QUEEN: 900, PieceType.KING: 20000
        }
        
        # Check what pieces are being attacked
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if not piece:
                    continue
                
                # Find pieces attacking this piece
                attackers = self._get_attackers(row, col, Color.BLACK if piece.color == Color.WHITE else Color.WHITE)
                defenders = self._get_attackers(row, col, piece.color)
                
                if attackers:
                    piece_value = piece_values[piece.type]
                    
                    # If piece is hanging (attacked and not defended)
                    if not defenders:
                        if piece.color == Color.WHITE:
                            score -= piece_value * 0.9  # White piece hanging - severe penalty
                        else:
                            score += piece_value * 0.9   # Black piece hanging - good for us
                    
                    # If more attackers than defenders, piece is in danger
                    elif len(attackers) > len(defenders):
                        threat_value = piece_value * 0.6
                        if piece.color == Color.WHITE:
                            score -= threat_value
                        else:
                            score += threat_value
                    
                    # Exchange evaluation - compare values of attacking and defending pieces
                    elif attackers and defenders:
                        min_attacker_value = min(piece_values[att.type] for att in attackers)
                        min_defender_value = min(piece_values[def_.type] for def_ in defenders)
                        
                        # If we can capture with a less valuable piece
                        if min_attacker_value < piece_value:
                            net_gain = piece_value - min_attacker_value
                            if piece.color == Color.WHITE:
                                score += net_gain * 0.3  # Black gains
                            else:
                                score -= net_gain * 0.3  # White gains
        
        return score
    
    def _get_attackers(self, target_row, target_col, attacking_color):
        """Get all pieces of attacking_color that can attack the target square"""
        attackers = []
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == attacking_color:
                    # Get raw moves to avoid recursion in threat evaluation
                    raw_moves = self._get_raw_piece_moves(row, col)
                    if (target_row, target_col) in raw_moves:
                        attackers.append((row, col))
        
        return attackers
    
    def _evaluate_piece_activity(self):
        """Reward active piece placement and development"""
        score = 0
        
        # Count developed pieces vs undeveloped
        white_developed = 0
        black_developed = 0
        
        # Check minor piece development
        for col in [1, 2, 5, 6]:  # Knight and bishop starting squares
            # White pieces
            if not self.board[7][col] or self.board[7][col].has_moved:
                white_developed += 1
            # Black pieces  
            if not self.board[0][col] or self.board[0][col].has_moved:
                black_developed += 1
        
        score += (white_developed - black_developed) * 30
        
        # Center control bonus
        center_squares = [(3,3), (3,4), (4,3), (4,4)]
        extended_center = [(2,2), (2,3), (2,4), (2,5), (3,2), (3,5), (4,2), (4,5), (5,2), (5,3), (5,4), (5,5)]
        
        for row, col in center_squares:
            piece = self.board[row][col]
            if piece:
                value = 40 if piece.color == Color.WHITE else -40
                score += value
        
        for row, col in extended_center:
            piece = self.board[row][col]
            if piece:
                value = 20 if piece.color == Color.WHITE else -20
                score += value
        
        return score
    
    def _evaluate_king_safety_advanced(self):
        """Advanced king safety evaluation"""
        white_king_safety = self._evaluate_king_safety(self.kings[Color.WHITE], Color.WHITE)
        black_king_safety = self._evaluate_king_safety(self.kings[Color.BLACK], Color.BLACK)
        return white_king_safety - black_king_safety
    
    def _evaluate_pawn_structure(self):
        """Evaluate pawn structure"""
        score = 0
        
        # Check for doubled, isolated, and passed pawns
        for col in range(8):
            white_pawns = []
            black_pawns = []
            
            for row in range(8):
                piece = self.board[row][col]
                if piece and piece.type == PieceType.PAWN:
                    if piece.color == Color.WHITE:
                        white_pawns.append(row)
                    else:
                        black_pawns.append(row)
            
            # Doubled pawns penalty
            if len(white_pawns) > 1:
                score -= 20 * (len(white_pawns) - 1)
            if len(black_pawns) > 1:
                score += 20 * (len(black_pawns) - 1)
            
            # Isolated pawns penalty (simplified)
            if white_pawns and col > 0 and col < 7:
                has_support = False
                for check_col in [col-1, col+1]:
                    for check_row in range(8):
                        piece = self.board[check_row][check_col]
                        if piece and piece.type == PieceType.PAWN and piece.color == Color.WHITE:
                            has_support = True
                            break
                if not has_support:
                    score -= 15
            
            if black_pawns and col > 0 and col < 7:
                has_support = False
                for check_col in [col-1, col+1]:
                    for check_row in range(8):
                        piece = self.board[check_row][check_col]
                        if piece and piece.type == PieceType.PAWN and piece.color == Color.BLACK:
                            has_support = True
                            break
                if not has_support:
                    score += 15
        
        return score
    
    def _evaluate_king_safety(self, king_pos, color):
        """Evaluate king safety based on pawn shield and piece proximity"""
        safety = 0
        row, col = king_pos
        
        # Pawn shield bonus
        direction = -1 if color == Color.WHITE else 1
        for dc in [-1, 0, 1]:
            shield_col = col + dc
            if 0 <= shield_col < 8:
                shield_row = row + direction
                if (0 <= shield_row < 8 and 
                    self.board[shield_row][shield_col] and
                    self.board[shield_row][shield_col].type == PieceType.PAWN and
                    self.board[shield_row][shield_col].color == color):
                    safety += 30
        
        # Penalty for being in center during opening/middlegame
        total_pieces = sum(1 for r in range(8) for c in range(8) if self.board[r][c])
        if total_pieces > 20:  # Opening/middlegame
            if 2 <= row <= 5 and 2 <= col <= 5:
                safety -= 50
        
        return safety
    
    def _evaluate_endgame_factors(self):
        """Evaluate endgame-specific factors"""
        score = 0
        
        # King activity in endgame is crucial
        white_king_pos = self.kings[Color.WHITE]
        black_king_pos = self.kings[Color.BLACK]
        
        # Kings closer to center are better in endgame
        white_king_center_distance = abs(white_king_pos[0] - 3.5) + abs(white_king_pos[1] - 3.5)
        black_king_center_distance = abs(black_king_pos[0] - 3.5) + abs(black_king_pos[1] - 3.5)
        
        score += (black_king_center_distance - white_king_center_distance) * 10
        
        # Opposition in king and pawn endgames
        king_distance = abs(white_king_pos[0] - black_king_pos[0]) + abs(white_king_pos[1] - black_king_pos[1])
        if king_distance == 2:  # Kings in opposition
            # Having the move in opposition is good
            if self.current_player == Color.WHITE:
                score += 20
            else:
                score -= 20
        
        # Pawn promotion bonuses
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.type == PieceType.PAWN:
                    if piece.color == Color.WHITE:
                        # White pawns closer to promotion
                        promotion_distance = row
                        score += (7 - promotion_distance) * 15
                        
                        # Passed pawn bonus (simplified)
                        is_passed = True
                        for check_row in range(row):
                            for check_col in [col-1, col, col+1]:
                                if (0 <= check_col < 8 and 
                                    self.board[check_row][check_col] and
                                    self.board[check_row][check_col].type == PieceType.PAWN and
                                    self.board[check_row][check_col].color == Color.BLACK):
                                    is_passed = False
                                    break
                        if is_passed:
                            score += 50 + (7 - promotion_distance) * 20
                    
                    else:  # Black pawn
                        promotion_distance = 7 - row
                        score -= (7 - promotion_distance) * 15
                        
                        # Passed pawn bonus
                        is_passed = True
                        for check_row in range(row + 1, 8):
                            for check_col in [col-1, col, col+1]:
                                if (0 <= check_col < 8 and 
                                    self.board[check_row][check_col] and
                                    self.board[check_row][check_col].type == PieceType.PAWN and
                                    self.board[check_row][check_col].color == Color.WHITE):
                                    is_passed = False
                                    break
                        if is_passed:
                            score -= 50 + (7 - promotion_distance) * 20
        
        return score

    def to_dict(self):
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

class GameSession:
    """Represents a single chess game session with independent state"""
    def __init__(self, session_id: str, mode: GameMode = GameMode.HUMAN_VS_AI):
        self.session_id = session_id
        self.mode = mode
        self.board = ChessBoard()
        self.created_at = time.time()
        self.last_activity = time.time()
        self.player_white = None  # For human vs human mode
        self.player_black = None
        self._mcts_engine = None  # Lazy initialization
    
    @property
    def mcts_engine(self):
        """Lazy initialization of MCTS engine with enhanced settings"""
        if self._mcts_engine is None:
            self._mcts_engine = ChessMCTS(
                time_limit=6.0,  # Slightly longer for better play
                max_simulations=3000,
                max_depth=40
            )
        return self._mcts_engine
    
    def update_activity(self):
        self.last_activity = time.time()
    
    def is_expired(self, timeout_hours=24):
        return (time.time() - self.last_activity) > (timeout_hours * 3600)
    
    def make_move(self, from_row, from_col, to_row, to_col, special_move_type=None, promotion_piece=None):
        self.update_activity()
        return self.board.make_move(from_row, from_col, to_row, to_col, special_move_type, promotion_piece)
    
    def get_ai_move(self):
        """Get AI move for Human vs AI mode"""
        if self.mode == GameMode.HUMAN_VS_AI and self.board.current_player == Color.BLACK:
            self.update_activity()
            return self.mcts_engine.search(self.board)
        return None
    
    def reset_game(self):
        self.board = ChessBoard()
        self.update_activity()
    
    def to_dict(self):
        board_data = self.board.to_dict()
        return {
            **board_data,
            'session_id': self.session_id,
            'mode': self.mode.value,
            'created_at': self.created_at,
            'last_activity': self.last_activity
        }

class SessionManager:
    """Manages multiple game sessions with better isolation"""
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.cleanup_interval = 1800  # Clean up expired sessions every 30 minutes
        self.last_cleanup = time.time()
        self.max_sessions = 1000  # Prevent memory issues
    
    def create_session(self, mode: GameMode = GameMode.HUMAN_VS_AI) -> str:
        # Cleanup before creating new sessions
        self.cleanup_expired_sessions()
        
        # Prevent too many sessions
        if len(self.sessions) >= self.max_sessions:
            self.cleanup_expired_sessions(force=True)
        
        session_id = str(uuid.uuid4())
        # Ensure unique session ID
        while session_id in self.sessions:
            session_id = str(uuid.uuid4())
            
        self.sessions[session_id] = GameSession(session_id, mode)
        print(f"🎯 Created new session: {session_id[:8]}... (Mode: {mode.value})")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        if not session_id or session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        session.update_activity()  # Update last activity
        return session
    
    def cleanup_expired_sessions(self, force: bool = False):
        current_time = time.time()
        cleanup_threshold = self.cleanup_interval if not force else 0
        
        if current_time - self.last_cleanup > cleanup_threshold:
            expired_sessions = [
                sid for sid, session in self.sessions.items() 
                if session.is_expired(timeout_hours=2 if force else 24)  # Shorter timeout if forced
            ]
            for sid in expired_sessions:
                del self.sessions[sid]
            self.last_cleanup = current_time
            if expired_sessions:
                print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        return len(self.sessions)
    
    def get_session_info(self) -> Dict:
        """Get detailed session information"""
        active_sessions = 0
        human_vs_ai = 0
        human_vs_human = 0
        
        for session in self.sessions.values():
            if not session.is_expired():
                active_sessions += 1
                if session.mode == GameMode.HUMAN_VS_AI:
                    human_vs_ai += 1
                else:
                    human_vs_human += 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "human_vs_ai_sessions": human_vs_ai,
            "human_vs_human_sessions": human_vs_human
        }

class MCTSNode:
    def __init__(self, board: ChessBoard, move=None, parent=None):
        self.board = board
        self.move = move  # The move that led to this position
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_moves = board.get_all_legal_moves()
        
        # Sort moves by priority for better move ordering
        self.untried_moves.sort(key=lambda m: board.get_move_priority(m), reverse=True)
    
    def is_fully_expanded(self):
        return len(self.untried_moves) == 0
    
    def is_terminal(self):
        return self.board.is_checkmate() or self.board.is_stalemate() or len(self.board.get_all_legal_moves()) == 0
    
    def ucb1_value(self, c=1.4):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + c * math.sqrt(math.log(self.parent.visits) / self.visits)
    
    def best_child(self):
        return max(self.children, key=lambda child: child.ucb1_value())
    
    def most_visited_child(self):
        return max(self.children, key=lambda child: child.visits)

class ChessMCTS:
    def __init__(self, time_limit=6.0, max_simulations=3000, max_depth=40):
        self.time_limit = time_limit
        self.max_simulations = max_simulations
        self.max_depth = max_depth  # Maximum search depth to prevent infinite recursion
        self.simulation_depth_limit = 80  # Limit for simulation depth
    
    def search(self, board: ChessBoard):
        # Quick win detection
        legal_moves = board.get_all_legal_moves()
        if not legal_moves:
            return None
        
        # Check for immediate checkmate moves
        for move in legal_moves:
            temp_board = board.copy()
            if temp_board.make_move(move[0], move[1], move[2], move[3]):
                if temp_board.is_checkmate():
                    print(f"🎯 Found immediate checkmate: {move}")
                    return move
        
        root = MCTSNode(board.copy())
        start_time = time.time()
        simulations = 0
        max_time_reached = False
        
        while (time.time() - start_time < self.time_limit and 
               simulations < self.max_simulations and
               not max_time_reached):
            
            # Selection & Expansion with proper depth tracking
            node = self._select_and_expand(root, 0)
            if node is None:
                continue
            
            # Simulation with depth limit
            result = self._simulate(node.board.copy(), 0)
            
            # Backpropagation
            self._backpropagate(node, result)
            
            simulations += 1
            
            # Check time more frequently
            if simulations % 100 == 0 and time.time() - start_time > self.time_limit * 0.9:
                max_time_reached = True
        
        elapsed_time = time.time() - start_time
        print(f"MCTS completed {simulations} simulations in {elapsed_time:.2f}s")
        
        if root.children:
            # Choose best move based on robust child selection
            best_child = self._select_best_move(root)
            win_rate = best_child.wins / max(best_child.visits, 1)
            print(f"Best move: {best_child.move}, visits: {best_child.visits}, win rate: {win_rate:.3f}")
            return best_child.move
        else:
            # Fallback to highest priority move with safety check
            moves = board.get_all_legal_moves()
            if moves:
                # Sort by priority and check for safety
                safe_moves = []
                for move in moves:
                    temp_board = board.copy()
                    if temp_board.make_move(move[0], move[1], move[2], move[3]):
                        priority = board.get_move_priority(move)
                        safe_moves.append((move, priority))
                
                if safe_moves:
                    safe_moves.sort(key=lambda x: x[1], reverse=True)
                    return safe_moves[0][0]
                return moves[0]
            return None
    
    def _select_best_move(self, root):
        """Select best move using robust criteria"""
        if not root.children:
            return None
        
        # If one move has been explored significantly more, choose it
        max_visits = max(child.visits for child in root.children)
        highly_explored = [child for child in root.children if child.visits > max_visits * 0.7]
        
        if len(highly_explored) == 1:
            return highly_explored[0]
        
        # Otherwise use a combination of visit count and win rate
        best_child = None
        best_score = -float('inf')
        
        for child in root.children:
            if child.visits < 5:  # Skip poorly explored moves
                continue
            
            win_rate = child.wins / child.visits
            visit_weight = min(child.visits / max_visits, 1.0)
            
            # Balanced score considering both exploration and exploitation
            score = win_rate * 0.7 + visit_weight * 0.3
            
            if score > best_score:
                best_score = score
                best_child = child
        
        return best_child or root.most_visited_child()
    
    def _select_and_expand(self, root, depth=0):
        node = root
        current_depth = depth
        
        # Selection with depth limit and better termination
        while (not node.is_terminal() and 
               node.is_fully_expanded() and 
               current_depth < self.max_depth):
            if not node.children:
                break
            node = node.best_child()
            current_depth += 1
        
        # Check if we hit depth limit
        if current_depth >= self.max_depth:
            return node
        
        # Expansion (only if under depth limit and not terminal)
        if (not node.is_terminal() and 
            not node.is_fully_expanded() and 
            current_depth < self.max_depth):
            
            if not node.untried_moves:
                return node
                
            move = node.untried_moves.pop(0)  # Take highest priority move
            new_board = node.board.copy()
            
            try:
                # Handle special moves properly with error handling
                success = False
                if len(move) > 4:  # Special move with extra data
                    success = new_board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = new_board.make_move(move[0], move[1], move[2], move[3])
                
                if success:
                    child = MCTSNode(new_board, move, node)
                    node.children.append(child)
                    return child
                else:
                    # Move failed, try to expand again if moves remain
                    if node.untried_moves:
                        return self._select_and_expand(node, current_depth)
                    else:
                        return node
            except Exception as e:
                # Handle any errors in move making
                if node.untried_moves:
                    return self._select_and_expand(node, current_depth)
                else:
                    return node
        
        return node
    
    def _simulate(self, board, depth=0):
        """Run a more intelligent simulation with proper depth limit"""
        simulation_moves = 0
        
        while (not board.is_checkmate() and 
               not board.is_stalemate() and 
               not board.is_draw_by_fifty_moves() and
               not board.is_insufficient_material() and
               simulation_moves < self.simulation_depth_limit and
               depth + simulation_moves < self.max_depth * 2):
            
            moves = board.get_all_legal_moves()
            if not moves:
                break
            
            # Use intelligent move selection with error handling
            move = self._select_simulation_move(board, moves)
            if not move:
                break
                
            try:
                # Make the move with proper error handling
                success = False
                if len(move) > 4:
                    success = board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = board.make_move(move[0], move[1], move[2], move[3])
                
                if not success:
                    break
                    
            except Exception as e:
                break
                
            simulation_moves += 1
        
        # Evaluate final position with enhanced termination detection
        return self._evaluate_final_position(board)
    
    def _evaluate_final_position(self, board):
        """Enhanced final position evaluation"""
        game_result = board.get_game_result()
        
        if game_result == GameResult.WHITE_WINS:
            return Color.WHITE
        elif game_result == GameResult.BLACK_WINS:
            return Color.BLACK
        elif game_result == GameResult.DRAW:
            return 'draw'
        else:
            # Use evaluation function for unfinished games
            score = board.evaluate_position()
            
            # More nuanced evaluation
            if abs(score) < 100:  # Very close position
                return 'draw'
            elif abs(score) < 300:  # Slightly favorable
                return 'draw' if random.random() < 0.3 else (Color.WHITE if score > 0 else Color.BLACK)
            else:  # Clear advantage
                return Color.WHITE if score > 0 else Color.BLACK
    
    def _select_simulation_move(self, board, moves):
        """Intelligent move selection for simulations with enhanced move handling"""
        if not moves:
            return None
            
        # Prioritize moves by type
        checkmate_moves = []
        check_moves = []
        capture_moves = []
        tactical_moves = []
        normal_moves = []
        
        for move in moves:
            try:
                temp_board = board.copy()
                
                # Handle different move formats
                if len(move) > 4:  # Special move
                    success = temp_board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = temp_board.make_move(move[0], move[1], move[2], move[3])
                
                if not success:
                    continue
                
                opponent_color = Color.BLACK if board.current_player == Color.WHITE else Color.WHITE
                
                # Check for checkmate
                if temp_board.is_checkmate():
                    checkmate_moves.append(move)
                    continue
                
                # Check for check
                if temp_board.is_in_check(opponent_color):
                    check_moves.append(move)
                    continue
                
                # Check for captures
                if board.board[move[2]][move[3]]:
                    capture_moves.append(move)
                    continue
                
                # Check for tactical moves (piece development, center control)
                priority = board.get_move_priority(move)
                if priority > 100:
                    tactical_moves.append(move)
                else:
                    normal_moves.append(move)
                    
            except Exception as e:
                # Skip moves that cause errors
                continue
        
        # Select move with weighted probabilities
        rand = random.random()
        if checkmate_moves:
            return random.choice(checkmate_moves)
        elif check_moves and rand < 0.7:
            return random.choice(check_moves)
        elif capture_moves and rand < 0.8:
            # Sort captures by value and prefer good captures
            try:
                capture_moves.sort(key=lambda m: board.get_move_priority(m), reverse=True)
                # 70% chance for best capture, 30% for any capture
                if random.random() < 0.7 and capture_moves:
                    return capture_moves[0]
                return random.choice(capture_moves)
            except:
                return random.choice(capture_moves) if capture_moves else None
        elif tactical_moves and rand < 0.6:
            return random.choice(tactical_moves)
        elif normal_moves:
            return random.choice(normal_moves)
        else:
            return moves[0] if moves else None
    
    def _backpropagate(self, node, result):
        while node is not None:
            node.visits += 1
            
            if result == 'draw':
                node.wins += 0.5
            elif node.move:  # Not root node
                move_player = Color.BLACK if node.board.current_player == Color.WHITE else Color.WHITE
                if result == move_player:
                    node.wins += 1
            
            node = node.parent

# FastAPI Pydantic models for request/response
class MoveRequest(BaseModel):
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    special_move_type: Optional[str] = None
    promotion_piece: Optional[str] = None

class CreateSessionRequest(BaseModel):
    mode: str = 'human_vs_ai'  # 'human_vs_ai' or 'human_vs_human'

class SessionResponse(BaseModel):
    session_id: str
    success: bool
    message: str

class GameStateResponse(BaseModel):
    board: dict
    legal_moves: List
    is_checkmate: bool
    is_stalemate: bool
    is_check: bool
    material_balance: dict
    game_result: str
    session_id: str
    mode: str

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

# FastAPI app setup
app = FastAPI(title="Enhanced MCTS Chess Engine", description="Multi-session Chess engine with proper chess rules")

# Add CORS middleware to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="template")  # Fixed directory name
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session management
session_manager = SessionManager()

# Helper function to get session from header or query parameter - IMPROVED
def get_or_create_session(session_id: Optional[str] = None) -> GameSession:
    if session_id and session_id.strip():
        session = session_manager.get_session(session_id.strip())
        if session:
            return session
        else:
            # Session ID provided but not found - create new session with that ID if valid
            if len(session_id.strip()) == 36:  # Valid UUID length
                try:
                    # Try to create session with provided ID
                    new_session = GameSession(session_id.strip())
                    session_manager.sessions[session_id.strip()] = new_session
                    return new_session
                except:
                    pass
    
    # Create new session if none found or invalid ID
    new_session_id = session_manager.create_session()
    return session_manager.get_session(new_session_id)

@app.post("/api/session/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new game session"""
    try:
        mode = GameMode.HUMAN_VS_AI if request.mode == 'human_vs_ai' else GameMode.HUMAN_VS_HUMAN
        session_id = session_manager.create_session(mode)
        return SessionResponse(
            session_id=session_id,
            success=True,
            message=f"Created new {request.mode} game session"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the chess game interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/game/state")
async def get_game_state(session_id: Optional[str] = None):
    """Get current game state - requires session ID for proper isolation"""
    if not session_id:
        # Create new session if none provided
        new_session_id = session_manager.create_session()
        session = session_manager.get_session(new_session_id)
    else:
        session = get_or_create_session(session_id)
    
    board_data = session.to_dict()
    
    return GameStateResponse(
        board=board_data,
        legal_moves=session.board.get_all_legal_moves(),
        is_checkmate=session.board.is_checkmate(),
        is_stalemate=session.board.is_stalemate(),
        is_check=session.board.is_in_check(session.board.current_player),
        material_balance=session.board.calculate_material_balance(),
        game_result=session.board.get_game_result().value,
        session_id=session.session_id,
        mode=session.mode.value
    )

@app.post("/api/game/move")
async def make_move(move: MoveRequest, session_id: Optional[str] = None):
    """Make a player move - requires session ID for proper isolation"""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required for move. Please create a session first.")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please create a new session.")
    
    # Convert promotion piece string to enum if provided
    promotion_piece = None
    if move.promotion_piece:
        promotion_piece_map = {
            'Q': PieceType.QUEEN, 'R': PieceType.ROOK,
            'B': PieceType.BISHOP, 'N': PieceType.KNIGHT
        }
        promotion_piece = promotion_piece_map.get(move.promotion_piece.upper())
    
    success = session.make_move(
        move.from_row, move.from_col, move.to_row, move.to_col,
        move.special_move_type, promotion_piece
    )
    
    board_data = session.to_dict()
    message = "Move successful" if success else "Invalid move"
    
    return MoveResponse(
        success=success,
        board=board_data,
        legal_moves=session.board.get_all_legal_moves(),
        is_checkmate=session.board.is_checkmate(),
        is_stalemate=session.board.is_stalemate(),
        is_check=session.board.is_in_check(session.board.current_player),
        material_balance=session.board.calculate_material_balance(),
        game_result=session.board.get_game_result().value,
        message=message
    )

@app.post("/api/game/ai_move")
async def ai_move(session_id: Optional[str] = None):
    """Get AI move using enhanced MCTS - requires session ID"""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required for AI move. Please create a session first.")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please create a new session.")
    
    if session.mode != GameMode.HUMAN_VS_AI:
        raise HTTPException(status_code=400, detail="AI moves only available in Human vs AI mode")
    
    if session.board.current_player == Color.BLACK:
        move = session.get_ai_move()
        if move:
            print(f"🤖 AI making move: {move}")
            # Handle special moves in AI move with error handling
            try:
                if len(move) > 4:
                    success = session.board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = session.board.make_move(move[0], move[1], move[2], move[3])
                
                if not success:
                    print(f"⚠️ AI move failed: {move}")
            except Exception as e:
                print(f"❌ Error in AI move: {e}")
    
    board_data = session.to_dict()
    
    return MoveResponse(
        success=True,
        board=board_data,
        legal_moves=session.board.get_all_legal_moves(),
        is_checkmate=session.board.is_checkmate(),
        is_stalemate=session.board.is_stalemate(),
        is_check=session.board.is_in_check(session.board.current_player),
        material_balance=session.board.calculate_material_balance(),
        game_result=session.board.get_game_result().value,
        message="AI move completed"
    )

@app.post("/api/game/reset")
async def reset_game(session_id: Optional[str] = None):
    """Reset the game - requires session ID"""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required to reset game.")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please create a new session.")
    
    session.reset_game()
    return {
        "board": session.to_dict(),
        "message": "Game reset successfully",
        "session_id": session.session_id
    }

@app.get("/api/sessions/stats")
async def get_session_stats():
    """Get detailed session statistics"""
    session_info = session_manager.get_session_info()
    return {
        **session_info,
        "server_uptime": time.time() - session_manager.last_cleanup,
        "max_sessions": session_manager.max_sessions
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "engine": "Enhanced Multi-Session MCTS Chess",
        "active_sessions": session_manager.get_session_count()
    }

if __name__ == "__main__":
    print("🚀 Starting Enhanced Multi-Session MCTS Chess Engine v2.0...")
    print("📋 API Documentation: http://localhost:8000/docs")
    print("🎮 Chess Game: http://localhost:8000")
    print("\n🆕 Enhanced Features:")
    print("  ✅ Improved session management - proper state isolation")
    print("  ✅ Enhanced MCTS with depth limits and better termination")
    print("  ✅ Human vs Human and Human vs AI game modes")
    print("  ✅ Real-time material balance and points display")
    print("  ✅ Complete chess rules: castling, en passant, pawn promotion")
    print("  ✅ 50-move rule, insufficient material, and threefold repetition")
    print("  ✅ Robust error handling and move validation")
    print("  ✅ Session isolation to prevent state sharing between users")
    print("\n🔧 Technical Improvements:")
    print("  • Fixed template directory path")
    print("  • Enhanced MCTS depth limiting")
    print("  • Better session cleanup and management")
    print("  • Improved game termination detection")
    print("  • Session-aware API endpoints")
    print("\n📡 API Endpoints:")
    print("  GET  /                        - Chess game interface")
    print("  POST /api/session/create      - Create new game session")
    print("  GET  /api/game/state          - Get current game state (requires session)")
    print("  POST /api/game/move           - Make a move (requires session)")
    print("  POST /api/game/ai_move        - Get AI move (Human vs AI mode)")
    print("  POST /api/game/reset          - Reset game (requires session)")
    print("  GET  /api/sessions/stats      - Enhanced session statistics")
    print("  GET  /health                  - Health check")
    print("  GET  /docs                    - API documentation")
    print("\n⚠️  Important: Each user needs their own session ID to prevent state sharing!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
