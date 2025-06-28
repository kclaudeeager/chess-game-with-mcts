"""
Chess position evaluation for strategic play.
"""
from typing import Dict
from .chess_board import ChessBoard, Color, PieceType


class ChessEvaluator:
    """Advanced chess position evaluator with strategic and tactical awareness"""
    
    def __init__(self):
        # Piece values
        self.piece_values = {
            PieceType.PAWN: 100,
            PieceType.KNIGHT: 320,
            PieceType.BISHOP: 330,
            PieceType.ROOK: 500,
            PieceType.QUEEN: 900,
            PieceType.KING: 20000
        }
        
        # Piece-Square Tables
        self.pawn_table = [
            [ 0,  0,  0,  0,  0,  0,  0,  0],
            [50, 50, 50, 50, 50, 50, 50, 50],
            [10, 10, 20, 30, 30, 20, 10, 10],
            [ 5,  5, 10, 25, 25, 10,  5,  5],
            [ 0,  0,  0, 20, 20,  0,  0,  0],
            [ 5, -5,-10,  0,  0,-10, -5,  5],
            [ 5, 10, 10,-20,-20, 10, 10,  5],
            [ 0,  0,  0,  0,  0,  0,  0,  0]
        ]
        
        self.knight_table = [
            [-50,-40,-30,-30,-30,-30,-40,-50],
            [-40,-20,  0,  0,  0,  0,-20,-40],
            [-30,  0, 10, 15, 15, 10,  0,-30],
            [-30,  5, 15, 20, 20, 15,  5,-30],
            [-30,  0, 15, 20, 20, 15,  0,-30],
            [-30,  5, 10, 15, 15, 10,  5,-30],
            [-40,-20,  0,  5,  5,  0,-20,-40],
            [-50,-40,-30,-30,-30,-30,-40,-50]
        ]
        
        self.bishop_table = [
            [-20,-10,-10,-10,-10,-10,-10,-20],
            [-10,  0,  0,  0,  0,  0,  0,-10],
            [-10,  0,  5, 10, 10,  5,  0,-10],
            [-10,  5,  5, 10, 10,  5,  5,-10],
            [-10,  0, 10, 10, 10, 10,  0,-10],
            [-10, 10, 10, 10, 10, 10, 10,-10],
            [-10,  5,  0,  0,  0,  0,  5,-10],
            [-20,-10,-10,-10,-10,-10,-10,-20]
        ]
        
        self.rook_table = [
            [ 0,  0,  0,  0,  0,  0,  0,  0],
            [ 5, 10, 10, 10, 10, 10, 10,  5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [ 0,  0,  0,  5,  5,  0,  0,  0]
        ]
        
        self.queen_table = [
            [-20,-10,-10, -5, -5,-10,-10,-20],
            [-10,  0,  0,  0,  0,  0,  0,-10],
            [-10,  0,  5,  5,  5,  5,  0,-10],
            [ -5,  0,  5,  5,  5,  5,  0, -5],
            [  0,  0,  5,  5,  5,  5,  0, -5],
            [-10,  5,  5,  5,  5,  5,  0,-10],
            [-10,  0,  5,  0,  0,  0,  0,-10],
            [-20,-10,-10, -5, -5,-10,-10,-20]
        ]
        
        self.king_middlegame_table = [
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-30,-40,-40,-50,-50,-40,-40,-30],
            [-20,-30,-30,-40,-40,-30,-30,-20],
            [-10,-20,-20,-20,-20,-20,-20,-10],
            [ 20, 20,  0,  0,  0,  0, 20, 20],
            [ 20, 30, 10,  0,  0, 10, 30, 20]
        ]
        
        self.king_endgame_table = [
            [-50,-40,-30,-20,-20,-30,-40,-50],
            [-30,-20,-10,  0,  0,-10,-20,-30],
            [-30,-10, 20, 30, 30, 20,-10,-30],
            [-30,-10, 30, 40, 40, 30,-10,-30],
            [-30,-10, 30, 40, 40, 30,-10,-30],
            [-30,-10, 20, 30, 30, 20,-10,-30],
            [-30,-30,  0,  0,  0,  0,-30,-30],
            [-50,-30,-30,-30,-30,-30,-30,-50]
        ]
        
        self.piece_tables = {
            PieceType.PAWN: self.pawn_table,
            PieceType.KNIGHT: self.knight_table,
            PieceType.BISHOP: self.bishop_table,
            PieceType.ROOK: self.rook_table,
            PieceType.QUEEN: self.queen_table
        }
    
    def evaluate_position(self, board: ChessBoard) -> int:
        """Evaluate chess position with strategic and tactical considerations"""
        score = 0
        total_pieces = self._count_total_pieces(board)
        is_endgame = total_pieces <= 16
        
        # 1. Material and positional evaluation
        score += self._evaluate_material_and_position(board, is_endgame)
        
        # 2. Tactical evaluation
        score += self._evaluate_threats(board)
        
        # 3. Checkmate and check bonuses
        score += self._evaluate_check_and_mate(board)
        
        # 4. Piece activity and development
        score += self._evaluate_piece_activity(board)
        
        # 5. King safety
        score += self._evaluate_king_safety(board)
        
        # 6. Pawn structure
        score += self._evaluate_pawn_structure(board)
        
        # 7. Endgame factors
        if is_endgame:
            score += self._evaluate_endgame_factors(board)
        
        return score
    
    def _count_total_pieces(self, board: ChessBoard) -> int:
        """Count total pieces on the board"""
        count = 0
        for row in range(8):
            for col in range(8):
                if board.board[row][col]:
                    count += 1
        return count
    
    def _evaluate_material_and_position(self, board: ChessBoard, is_endgame: bool) -> int:
        """Evaluate material balance with positional bonuses"""
        score = 0
        
        for row in range(8):
            for col in range(8):
                piece = board.board[row][col]
                if piece:
                    # Material value
                    material_value = self.piece_values[piece.type]
                    if piece.color == Color.WHITE:
                        score += material_value
                    else:
                        score -= material_value
                    
                    # Positional bonus
                    positional_bonus = self._get_positional_bonus(piece, row, col, is_endgame)
                    if piece.color == Color.WHITE:
                        score += positional_bonus
                    else:
                        score -= positional_bonus
        
        return score
    
    def _get_positional_bonus(self, piece, row: int, col: int, is_endgame: bool) -> int:
        """Get positional bonus for a piece"""
        if piece.type == PieceType.KING:
            table = self.king_endgame_table if is_endgame else self.king_middlegame_table
        else:
            table = self.piece_tables.get(piece.type)
        
        if not table:
            return 0
        
        # Flip table for black pieces
        if piece.color == Color.BLACK:
            return table[row][col]
        else:
            return table[7 - row][col]
    
    def _evaluate_threats(self, board: ChessBoard) -> int:
        """Evaluate piece threats and hanging pieces"""
        score = 0
        
        for row in range(8):
            for col in range(8):
                piece = board.board[row][col]
                if piece:
                    attackers = self._get_attackers(board, row, col, 
                                                  Color.BLACK if piece.color == Color.WHITE else Color.WHITE)
                    defenders = self._get_attackers(board, row, col, piece.color)
                    
                    if attackers and len(attackers) > len(defenders):
                        # Piece is hanging or under-defended
                        threat_value = self.piece_values[piece.type] // 10
                        if piece.color == Color.WHITE:
                            score -= threat_value
                        else:
                            score += threat_value
        
        return score
    
    def _get_attackers(self, board: ChessBoard, target_row: int, target_col: int, attacking_color: Color) -> list:
        """Get all pieces of attacking_color that can attack the target square"""
        attackers = []
        
        for row in range(8):
            for col in range(8):
                piece = board.board[row][col]
                if piece and piece.color == attacking_color:
                    raw_moves = board._get_raw_piece_moves(row, col)
                    if (target_row, target_col) in raw_moves:
                        attackers.append((row, col, piece))
        
        return attackers
    
    def _evaluate_check_and_mate(self, board: ChessBoard) -> int:
        """Evaluate check and checkmate situations"""
        score = 0
        
        if board.is_checkmate():
            if board.current_player == Color.WHITE:
                score -= 100000  # Black wins
            else:
                score += 100000  # White wins
        elif board.is_in_check(board.current_player):
            if board.current_player == Color.WHITE:
                score -= 50
            else:
                score += 50
        
        return score
    
    def _evaluate_piece_activity(self, board: ChessBoard) -> int:
        """Evaluate piece development and activity"""
        score = 0
        
        # Development bonus
        white_developed = 0
        black_developed = 0
        
        for col in [1, 2, 5, 6]:  # Knight and bishop starting squares
            if not board.board[7][col] or board.board[7][col].has_moved:
                white_developed += 1
            if not board.board[0][col] or board.board[0][col].has_moved:
                black_developed += 1
        
        score += (white_developed - black_developed) * 30
        
        # Center control
        center_squares = [(3, 3), (3, 4), (4, 3), (4, 4)]
        extended_center = [(2, 2), (2, 3), (2, 4), (2, 5), (3, 2), (3, 5), 
                          (4, 2), (4, 5), (5, 2), (5, 3), (5, 4), (5, 5)]
        
        for row, col in center_squares:
            piece = board.board[row][col]
            if piece:
                bonus = 40 if piece.color == Color.WHITE else -40
                score += bonus
        
        for row, col in extended_center:
            piece = board.board[row][col]
            if piece:
                bonus = 20 if piece.color == Color.WHITE else -20
                score += bonus
        
        return score
    
    def _evaluate_king_safety(self, board: ChessBoard) -> int:
        """Evaluate king safety"""
        white_safety = self._evaluate_king_safety_single(board, Color.WHITE)
        black_safety = self._evaluate_king_safety_single(board, Color.BLACK)
        return white_safety - black_safety
    
    def _evaluate_king_safety_single(self, board: ChessBoard, color: Color) -> int:
        """Evaluate king safety for one side"""
        safety = 0
        king_pos = board.kings[color]
        row, col = king_pos
        
        # Pawn shield bonus
        direction = -1 if color == Color.WHITE else 1
        for dc in [-1, 0, 1]:
            shield_col = col + dc
            if 0 <= shield_col < 8:
                shield_row = row + direction
                if (0 <= shield_row < 8 and 
                    board.board[shield_row][shield_col] and
                    board.board[shield_row][shield_col].type == PieceType.PAWN and
                    board.board[shield_row][shield_col].color == color):
                    safety += 30
        
        # Penalty for exposed king in opening/middlegame
        total_pieces = self._count_total_pieces(board)
        if total_pieces > 20:
            if 2 <= row <= 5 and 2 <= col <= 5:
                safety -= 50
        
        return safety
    
    def _evaluate_pawn_structure(self, board: ChessBoard) -> int:
        """Evaluate pawn structure"""
        score = 0
        
        for col in range(8):
            white_pawns = []
            black_pawns = []
            
            # Collect pawns in this file
            for row in range(8):
                piece = board.board[row][col]
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
            
            # Isolated pawns penalty
            if white_pawns and self._is_isolated_pawn(board, col, Color.WHITE):
                score -= 15
            if black_pawns and self._is_isolated_pawn(board, col, Color.BLACK):
                score += 15
        
        return score
    
    def _is_isolated_pawn(self, board: ChessBoard, col: int, color: Color) -> bool:
        """Check if pawns in this file are isolated"""
        for check_col in [col - 1, col + 1]:
            if 0 <= check_col < 8:
                for row in range(8):
                    piece = board.board[row][check_col]
                    if (piece and piece.type == PieceType.PAWN and 
                        piece.color == color):
                        return False
        return True
    
    def _evaluate_endgame_factors(self, board: ChessBoard) -> int:
        """Evaluate endgame-specific factors"""
        score = 0
        
        # King activity
        white_king_pos = board.kings[Color.WHITE]
        black_king_pos = board.kings[Color.BLACK]
        
        # Kings closer to center are better in endgame
        white_center_dist = abs(white_king_pos[0] - 3.5) + abs(white_king_pos[1] - 3.5)
        black_center_dist = abs(black_king_pos[0] - 3.5) + abs(black_king_pos[1] - 3.5)
        score += (black_center_dist - white_center_dist) * 10
        
        # Opposition bonus
        king_distance = abs(white_king_pos[0] - black_king_pos[0]) + abs(white_king_pos[1] - black_king_pos[1])
        if king_distance == 2:
            if board.current_player == Color.WHITE:
                score += 20
            else:
                score -= 20
        
        # Pawn promotion evaluation
        score += self._evaluate_pawn_promotion(board)
        
        return score
    
    def _evaluate_pawn_promotion(self, board: ChessBoard) -> int:
        """Evaluate pawn promotion potential"""
        score = 0
        
        for row in range(8):
            for col in range(8):
                piece = board.board[row][col]
                if piece and piece.type == PieceType.PAWN:
                    if piece.color == Color.WHITE:
                        promotion_distance = row
                        score += (7 - promotion_distance) * 15
                        
                        # Passed pawn bonus
                        if self._is_passed_pawn(board, row, col, Color.WHITE):
                            score += 50 + (7 - promotion_distance) * 20
                    else:
                        promotion_distance = 7 - row
                        score -= (7 - promotion_distance) * 15
                        
                        # Passed pawn bonus
                        if self._is_passed_pawn(board, row, col, Color.BLACK):
                            score -= 50 + (7 - promotion_distance) * 20
        
        return score
    
    def _is_passed_pawn(self, board: ChessBoard, row: int, col: int, color: Color) -> bool:
        """Check if a pawn is passed"""
        if color == Color.WHITE:
            for check_row in range(row):
                for check_col in [col - 1, col, col + 1]:
                    if (0 <= check_col < 8 and 
                        board.board[check_row][check_col] and
                        board.board[check_row][check_col].type == PieceType.PAWN and
                        board.board[check_row][check_col].color == Color.BLACK):
                        return False
        else:
            for check_row in range(row + 1, 8):
                for check_col in [col - 1, col, col + 1]:
                    if (0 <= check_col < 8 and 
                        board.board[check_row][check_col] and
                        board.board[check_row][check_col].type == PieceType.PAWN and
                        board.board[check_row][check_col].color == Color.WHITE):
                        return False
        return True
    
    def get_move_priority(self, board: ChessBoard, move: tuple) -> int:
        """Get priority score for a move"""
        score = 0
        from_row, from_col, to_row, to_col = move[:4]
        piece = board.board[from_row][from_col]
        target = board.board[to_row][to_col]
        
        # Prioritize captures
        if target:
            piece_values = {
                PieceType.QUEEN: 9, PieceType.ROOK: 5, PieceType.BISHOP: 3,
                PieceType.KNIGHT: 3, PieceType.PAWN: 1, PieceType.KING: 0
            }
            score += 10 + piece_values.get(target.type, 0)
        
        # Prioritize promotions
        if len(move) > 4 and move[4] == 'promotion':
            score += 20
        
        # Prioritize checks
        temp_board = board.copy()
        try:
            if len(move) > 4:
                temp_board.make_move(from_row, from_col, to_row, to_col, move[4])
            else:
                temp_board.make_move(from_row, from_col, to_row, to_col)
            
            opponent = Color.BLACK if board.current_player == Color.WHITE else Color.WHITE
            if temp_board.is_in_check(opponent):
                score += 15
        except Exception:
            pass
        
        # Center control bonus
        if (to_row, to_col) in [(3, 3), (3, 4), (4, 3), (4, 4)]:
            score += 2
        
        return score
