import random
import math
import time
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import json

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
            temp_board._make_move_unchecked(row, col, move[0], move[1])
            if not temp_board.is_in_check(self.current_player):
                legal_moves.append(move)
        
        return legal_moves
    
    def _get_pawn_moves(self, row, col):
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
            if (self.is_valid_position(new_row, new_col) and 
                self.board[new_row][new_col] and 
                self.board[new_row][new_col].color != piece.color):
                moves.append((new_row, new_col))
        
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
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if (self.is_valid_position(new_row, new_col) and 
                (not self.board[new_row][new_col] or 
                 self.board[new_row][new_col].color != self.board[row][col].color)):
                moves.append((new_row, new_col))
        
        return moves
    
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
            return self._get_pawn_moves(row, col)
        elif piece.type == PieceType.ROOK:
            return self._get_rook_moves(row, col)
        elif piece.type == PieceType.KNIGHT:
            return self._get_knight_moves(row, col)
        elif piece.type == PieceType.BISHOP:
            return self._get_bishop_moves(row, col)
        elif piece.type == PieceType.QUEEN:
            return self._get_queen_moves(row, col)
        elif piece.type == PieceType.KING:
            return self._get_king_moves(row, col)
        
        return []
    
    def make_move(self, from_row, from_col, to_row, to_col):
        if not self.is_valid_position(from_row, from_col) or not self.is_valid_position(to_row, to_col):
            return False
        
        piece = self.board[from_row][from_col]
        if not piece or piece.color != self.current_player:
            return False
        
        legal_moves = self.get_piece_moves(from_row, from_col)
        if (to_row, to_col) not in legal_moves:
            return False
        
        self._make_move_unchecked(from_row, from_col, to_row, to_col)
        return True
    
    def _make_move_unchecked(self, from_row, from_col, to_row, to_col):
        piece = self.board[from_row][from_col]
        
        # Update king position if king moved
        if piece.type == PieceType.KING:
            self.kings[piece.color] = (to_row, to_col)
        
        # Make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        piece.has_moved = True
        
        # Record move
        self.move_history.append((from_row, from_col, to_row, to_col))
        
        # Switch players
        self.current_player = Color.BLACK if self.current_player == Color.WHITE else Color.WHITE
    
    def is_checkmate(self):
        if not self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def is_stalemate(self):
        if self.is_in_check(self.current_player):
            return False
        return len(self.get_all_legal_moves()) == 0
    
    def evaluate_position(self):
        """Simple position evaluation for MCTS simulations"""
        piece_values = {
            PieceType.PAWN: 1,
            PieceType.KNIGHT: 3,
            PieceType.BISHOP: 3,
            PieceType.ROOK: 5,
            PieceType.QUEEN: 9,
            PieceType.KING: 0
        }
        
        score = 0
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    value = piece_values[piece.type]
                    if piece.color == Color.WHITE:
                        score += value
                    else:
                        score -= value
        
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
        
        return {
            'board': board_dict,
            'current_player': self.current_player.value,
            'move_history': self.move_history,
            'kings': {color.value: pos for color, pos in self.kings.items()}
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
        random.shuffle(self.untried_moves)  # Randomize move order
    
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
    def __init__(self, time_limit=5.0, max_simulations=1000):
        self.time_limit = time_limit
        self.max_simulations = max_simulations
    
    def search(self, board: ChessBoard):
        root = MCTSNode(board.copy())
        start_time = time.time()
        simulations = 0
        
        while (time.time() - start_time < self.time_limit and 
               simulations < self.max_simulations):
            
            # Selection & Expansion
            node = self._select_and_expand(root)
            
            # Simulation
            result = self._simulate(node.board.copy())
            
            # Backpropagation
            self._backpropagate(node, result)
            
            simulations += 1
        
        print(f"MCTS completed {simulations} simulations in {time.time() - start_time:.2f}s")
        
        if root.children:
            best_child = root.most_visited_child()
            return best_child.move
        else:
            # Fallback to random move
            moves = board.get_all_legal_moves()
            return random.choice(moves) if moves else None
    
    def _select_and_expand(self, root):
        node = root
        
        # Selection
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child()
        
        # Expansion
        if not node.is_terminal() and not node.is_fully_expanded():
            move = node.untried_moves.pop()
            new_board = node.board.copy()
            new_board.make_move(move[0], move[1], move[2], move[3])
            child = MCTSNode(new_board, move, node)
            node.children.append(child)
            return child
        
        return node
    
    def _simulate(self, board):
        """Run a random simulation to game end"""
        simulation_moves = 0
        max_simulation_moves = 100  # Prevent infinite games
        
        while (not board.is_checkmate() and not board.is_stalemate() and 
               simulation_moves < max_simulation_moves):
            
            moves = board.get_all_legal_moves()
            if not moves:
                break
            
            # Use slightly intelligent random moves (prefer captures)
            move = self._select_simulation_move(board, moves)
            board.make_move(move[0], move[1], move[2], move[3])
            simulation_moves += 1
        
        # Evaluate final position
        if board.is_checkmate():
            # Current player is in checkmate, so previous player won
            losing_player = board.current_player
            return Color.WHITE if losing_player == Color.BLACK else Color.BLACK
        elif board.is_stalemate():
            return 'draw'
        else:
            # Game didn't finish, evaluate position
            score = board.evaluate_position()
            if abs(score) < 2:  # Close position
                return 'draw'
            return Color.WHITE if score > 0 else Color.BLACK
    
    def _select_simulation_move(self, board, moves):
        """Select move for simulation with slight preference for captures"""
        captures = []
        normal_moves = []
        
        for move in moves:
            if board.board[move[2]][move[3]]:  # Target square has piece (capture)
                captures.append(move)
            else:
                normal_moves.append(move)
        
        # 70% chance to prefer captures if available
        if captures and random.random() < 0.7:
            return random.choice(captures)
        else:
            return random.choice(moves)
    
    def _backpropagate(self, node, result):
        while node is not None:
            node.visits += 1
            
            # Update wins based on the player who made the move leading to this node
            if result == 'draw':
                node.wins += 0.5
            elif node.move:  # Not root node
                # Determine which player made the move to reach this node
                move_player = Color.BLACK if node.board.current_player == Color.WHITE else Color.WHITE
                if result == move_player:
                    node.wins += 1
            
            node = node.parent

# Flask API for the chess engine
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global game state
current_game = ChessBoard()
mcts_engine = ChessMCTS(time_limit=3.0, max_simulations=500)

@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    return jsonify({
        'board': current_game.to_dict(),
        'legal_moves': current_game.get_all_legal_moves(),
        'is_checkmate': current_game.is_checkmate(),
        'is_stalemate': current_game.is_stalemate(),
        'is_check': current_game.is_in_check(current_game.current_player)
    })

@app.route('/api/game/move', methods=['POST'])
def make_move():
    data = request.json
    from_row = data['from_row']
    from_col = data['from_col']
    to_row = data['to_row']
    to_col = data['to_col']
    
    success = current_game.make_move(from_row, from_col, to_row, to_col)
    
    return jsonify({
        'success': success,
        'board': current_game.to_dict(),
        'is_checkmate': current_game.is_checkmate(),
        'is_stalemate': current_game.is_stalemate(),
        'is_check': current_game.is_in_check(current_game.current_player)
    })

@app.route('/api/game/ai_move', methods=['POST'])
def ai_move():
    if current_game.current_player == Color.BLACK:
        move = mcts_engine.search(current_game)
        if move:
            current_game.make_move(move[0], move[1], move[2], move[3])
    
    return jsonify({
        'board': current_game.to_dict(),
        'is_checkmate': current_game.is_checkmate(),
        'is_stalemate': current_game.is_stalemate(),
        'is_check': current_game.is_in_check(current_game.current_player)
    })

@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    global current_game
    current_game = ChessBoard()
    return jsonify({'board': current_game.to_dict()})

if __name__ == '__main__':
    print("Starting Chess MCTS Engine...")
    print("API endpoints:")
    print("  GET  /api/game/state     - Get current game state")
    print("  POST /api/game/move      - Make a move")
    print("  POST /api/game/ai_move   - Get AI move")
    print("  POST /api/game/reset     - Reset game")
    app.run(debug=True, port=5000)