"""
Monte Carlo Tree Search implementation for chess.
"""
import math
import random
import time
from typing import List, Optional, Tuple
from models.chess_board import ChessBoard, Color, GameResult
from models.evaluator import ChessEvaluator


class MCTSNode:
    """Node in the Monte Carlo Tree Search"""
    
    def __init__(self, board: ChessBoard, move=None, parent=None):
        self.board = board
        self.move = move  # The move that led to this position
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_moves = board.get_all_legal_moves()
        
        # Sort moves by priority for better move ordering
        self.evaluator = ChessEvaluator()
        self.untried_moves.sort(
            key=lambda m: self.evaluator.get_move_priority(board, m), 
            reverse=True
        )
    
    def is_fully_expanded(self) -> bool:
        """Check if all moves have been tried"""
        return len(self.untried_moves) == 0
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal node"""
        return (self.board.is_checkmate() or 
                self.board.is_stalemate() or 
                len(self.board.get_all_legal_moves()) == 0)
    
    def ucb1_value(self, c: float = 1.4) -> float:
        """Calculate UCB1 value for node selection"""
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + c * math.sqrt(math.log(self.parent.visits) / self.visits)
    
    def best_child(self) -> 'MCTSNode':
        """Get the child with the best UCB1 value"""
        return max(self.children, key=lambda child: child.ucb1_value())
    
    def most_visited_child(self) -> 'MCTSNode':
        """Get the most visited child"""
        return max(self.children, key=lambda child: child.visits)


class ChessMCTS:
    """Monte Carlo Tree Search for chess"""
    
    def __init__(self, time_limit: float = 6.0, max_simulations: int = 3000, max_depth: int = 40):
        self.time_limit = time_limit
        self.max_simulations = max_simulations
        self.max_depth = max_depth
        self.simulation_depth_limit = 80
        self.evaluator = ChessEvaluator()
    
    def search(self, board: ChessBoard) -> Optional[Tuple[int, int, int, int]]:
        """Perform MCTS search and return the best move"""
        # Quick checks
        legal_moves = board.get_all_legal_moves()
        if not legal_moves:
            return None
        
        # Check for immediate checkmate
        checkmate_move = self._find_checkmate_move(board, legal_moves)
        if checkmate_move:
            print(f"🎯 Found immediate checkmate: {checkmate_move}")
            return checkmate_move
        
        # Run MCTS
        root = MCTSNode(board.copy())
        start_time = time.time()
        simulations = 0
        
        while (time.time() - start_time < self.time_limit and 
               simulations < self.max_simulations):
            
            # Selection & Expansion
            node = self._select_and_expand(root, 0)
            if node is None:
                continue
            
            # Simulation
            result = self._simulate(node.board.copy(), 0)
            
            # Backpropagation
            self._backpropagate(node, result)
            
            simulations += 1
            
            # Early termination check
            if simulations % 100 == 0 and time.time() - start_time > self.time_limit * 0.9:
                break
        
        elapsed_time = time.time() - start_time
        print(f"MCTS completed {simulations} simulations in {elapsed_time:.2f}s")
        
        # Select best move
        if root.children:
            best_child = self._select_best_move(root)
            win_rate = best_child.wins / max(best_child.visits, 1)
            print(f"Best move: {best_child.move}, visits: {best_child.visits}, win rate: {win_rate:.3f}")
            return best_child.move
        else:
            # Fallback to highest priority move
            return self._fallback_move_selection(board, legal_moves)
    
    def _find_checkmate_move(self, board: ChessBoard, moves: List[Tuple]) -> Optional[Tuple]:
        """Find immediate checkmate moves"""
        for move in moves:
            temp_board = board.copy()
            if temp_board.make_move(move[0], move[1], move[2], move[3]):
                if temp_board.is_checkmate():
                    return move
        return None
    
    def _select_and_expand(self, root: MCTSNode, depth: int = 0) -> Optional[MCTSNode]:
        """Select and expand nodes in the tree"""
        node = root
        current_depth = depth
        
        # Selection phase - traverse down the tree
        while (not node.is_terminal() and 
               node.is_fully_expanded() and 
               current_depth < self.max_depth):
            if not node.children:
                break
            node = node.best_child()
            current_depth += 1
        
        # Check depth limit
        if current_depth >= self.max_depth:
            return node
        
        # Expansion phase - add new child node
        if (not node.is_terminal() and 
            not node.is_fully_expanded() and 
            current_depth < self.max_depth):
            
            if not node.untried_moves:
                return node
            
            move = node.untried_moves.pop(0)  # Take highest priority move
            new_board = node.board.copy()
            
            try:
                # Handle different move formats
                success = False
                if len(move) > 4:
                    success = new_board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = new_board.make_move(move[0], move[1], move[2], move[3])
                
                if success:
                    child = MCTSNode(new_board, move, node)
                    node.children.append(child)
                    return child
                else:
                    # Try again with remaining moves
                    if node.untried_moves:
                        return self._select_and_expand(node, current_depth)
                    else:
                        return node
            except Exception:
                # Handle move errors gracefully
                if node.untried_moves:
                    return self._select_and_expand(node, current_depth)
                else:
                    return node
        
        return node
    
    def _simulate(self, board: ChessBoard, depth: int = 0) -> Color:
        """Run a simulation from the given position"""
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
            
            # Intelligent move selection
            move = self._select_simulation_move(board, moves)
            if not move:
                break
            
            try:
                success = False
                if len(move) > 4:
                    success = board.make_move(move[0], move[1], move[2], move[3], move[4])
                else:
                    success = board.make_move(move[0], move[1], move[2], move[3])
                
                if not success:
                    break
            except Exception:
                break
            
            simulation_moves += 1
        
        return self._evaluate_final_position(board)
    
    def _select_simulation_move(self, board: ChessBoard, moves: List[Tuple]) -> Optional[Tuple]:
        """Select a move during simulation with intelligent heuristics"""
        if not moves:
            return None
        
        # Categorize moves
        checkmate_moves = []
        check_moves = []
        capture_moves = []
        tactical_moves = []
        normal_moves = []
        
        for move in moves:
            try:
                temp_board = board.copy()
                success = False
                if len(move) > 4:
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
                
                # Check for tactical moves
                priority = self.evaluator.get_move_priority(board, move)
                if priority > 100:
                    tactical_moves.append(move)
                else:
                    normal_moves.append(move)
                    
            except Exception:
                continue
        
        # Select move with weighted probabilities
        rand = random.random()
        if checkmate_moves:
            return random.choice(checkmate_moves)
        elif check_moves and rand < 0.7:
            return random.choice(check_moves)
        elif capture_moves and rand < 0.8:
            # Prefer good captures
            try:
                capture_moves.sort(key=lambda m: self.evaluator.get_move_priority(board, m), reverse=True)
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
    
    def _evaluate_final_position(self, board: ChessBoard) -> Color:
        """Evaluate the final position of a simulation"""
        game_result = board.get_game_result()
        
        if game_result == GameResult.WHITE_WINS:
            return Color.WHITE
        elif game_result == GameResult.BLACK_WINS:
            return Color.BLACK
        elif game_result == GameResult.DRAW:
            return 'draw'
        else:
            # Use evaluation function for unfinished games
            score = self.evaluator.evaluate_position(board)
            
            if abs(score) < 100:
                return 'draw'
            elif abs(score) < 300:
                return 'draw' if random.random() < 0.3 else (Color.WHITE if score > 0 else Color.BLACK)
            else:
                return Color.WHITE if score > 0 else Color.BLACK
    
    def _backpropagate(self, node: MCTSNode, result) -> None:
        """Backpropagate the simulation result up the tree"""
        while node is not None:
            node.visits += 1
            
            if result == 'draw':
                node.wins += 0.5
            elif node.move:  # Not root node
                move_player = Color.BLACK if node.board.current_player == Color.WHITE else Color.WHITE
                if result == move_player:
                    node.wins += 1
            
            node = node.parent
    
    def _select_best_move(self, root: MCTSNode) -> MCTSNode:
        """Select the best move using robust criteria"""
        if not root.children:
            return None
        
        # If one move is heavily explored, choose it
        max_visits = max(child.visits for child in root.children)
        highly_explored = [child for child in root.children if child.visits > max_visits * 0.7]
        
        if len(highly_explored) == 1:
            return highly_explored[0]
        
        # Use combination of win rate and visit count
        best_child = None
        best_score = -float('inf')
        
        for child in root.children:
            if child.visits < 5:  # Skip poorly explored moves
                continue
            
            win_rate = child.wins / child.visits
            visit_weight = min(child.visits / max_visits, 1.0)
            score = win_rate * 0.7 + visit_weight * 0.3
            
            if score > best_score:
                best_score = score
                best_child = child
        
        return best_child or root.most_visited_child()
    
    def _fallback_move_selection(self, board: ChessBoard, legal_moves: List[Tuple]) -> Optional[Tuple]:
        """Fallback move selection when MCTS fails"""
        if not legal_moves:
            return None
        
        # Sort by priority and return best move
        safe_moves = []
        for move in legal_moves:
            temp_board = board.copy()
            if temp_board.make_move(move[0], move[1], move[2], move[3]):
                priority = self.evaluator.get_move_priority(board, move)
                safe_moves.append((move, priority))
        
        if safe_moves:
            safe_moves.sort(key=lambda x: x[1], reverse=True)
            return safe_moves[0][0]
        
        return legal_moves[0]
