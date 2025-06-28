"""
RL-Enhanced MCTS implementation with data recording capabilities.
"""
import json
import random
import time
from collections import deque
from typing import Dict, Optional
from engines.mcts import ChessMCTS, MCTSNode
from models.chess_board import ChessBoard, Color
from data.rl_data import GameDataRecorder


class RLEnhancedMCTS(ChessMCTS):
    """MCTS enhanced with Reinforcement Learning for better move evaluation"""
    
    def __init__(self, time_limit: float = 6.0, max_simulations: int = 3000, 
                 max_depth: int = 40, rl_weight: float = 0.3, 
                 data_recorder: Optional[GameDataRecorder] = None):
        super().__init__(time_limit, max_simulations, max_depth)
        self.rl_weight = rl_weight
        self.data_recorder = data_recorder
        self.position_history = deque(maxlen=100)
        self.current_game_id = None
        self.move_number = 0
    
    def start_game_recording(self, session_id: str, game_mode: str):
        """Start recording a new game for RL training"""
        if self.data_recorder:
            self.current_game_id = self.data_recorder.start_game_recording(
                session_id, game_mode
            )
            self.move_number = 0
            self.position_history.clear()
    
    def search(self, board: ChessBoard) -> Optional[tuple]:
        """Enhanced search with RL-guided exploration - simplified reliable version"""
        print("🚀 RL MCTS search called")
        
        # Record position for RL
        if self.data_recorder and self.current_game_id:
            try:
                position_data = {
                    'game_id': self.current_game_id,
                    'move_number': self.move_number,
                    'position': json.dumps(board.to_dict()),
                    'player': board.current_player.value
                }
                self.position_history.append(position_data)
                self.data_recorder.record_position(position_data)
            except Exception as e:
                print(f"⚠️ RL MCTS: Error recording position: {e}")
        
        # Get legal moves first
        legal_moves = board.get_all_legal_moves()
        print(f"🎯 RL MCTS: Found {len(legal_moves)} legal moves")
        if not legal_moves:
            print("⚠️ RL MCTS: No legal moves available")
            return None
        
        # Quick checkmate check
        try:
            checkmate_move = self._find_checkmate_move(board, legal_moves)
            if checkmate_move:
                print(f"🎯 RL MCTS: Found checkmate move: {checkmate_move}")
                return checkmate_move
        except Exception as e:
            print(f"⚠️ RL MCTS: Error in checkmate check: {e}")
        
        # Use simplified RL-enhanced move selection instead of complex MCTS
        print("🔄 RL MCTS: Using simplified RL move selection")
        try:
            # Simple RL-enhanced move selection without complex dependencies
            move_scores = []
            for move in legal_moves:
                # Simple scoring without evaluator dependency
                score = self._simple_move_score(board, move)
                move_scores.append((move, score))
            
            # Sort by score and return best move
            move_scores.sort(key=lambda x: x[1], reverse=True)
            selected_move = move_scores[0][0]
            print(f"✅ RL MCTS: Selected move: {selected_move}")
            return selected_move
            
        except Exception as e:
            print(f"❌ RL MCTS: Error in move selection: {e}")
            # Absolute fallback - just return first legal move
            print(f"🆘 RL MCTS: Using first legal move: {legal_moves[0]}")
            return legal_moves[0]
    
    def _format_move_response(self, move: tuple, confidence: float, simulations: int) -> Dict:
        """Format move response for API"""
        if not move:
            return None
        
        return {
            'from': [move[0], move[1]],
            'to': [move[2], move[3]],
            'promotion': move[4] if len(move) > 4 else None,
            'confidence': confidence,
            'simulations': simulations
        }
    
    def _rl_select_and_expand(self, root: MCTSNode, depth: int = 0) -> Optional[MCTSNode]:
        """Select and expand nodes with RL guidance"""
        if depth > self.max_depth:
            return None
        
        node = root
        
        # RL-enhanced selection
        while not node.is_terminal() and node.is_fully_expanded():
            if not node.children:
                break
            
            best_child = None
            best_value = -float('inf')
            
            for child in node.children:
                traditional_ucb = child.ucb1_value()
                rl_value = self._get_rl_move_value(child.board, child.move)
                combined_value = traditional_ucb + self.rl_weight * rl_value
                
                if combined_value > best_value:
                    best_value = combined_value
                    best_child = child
            
            node = best_child or node.children[0]
            depth += 1
        
        # RL-guided expansion
        if not node.is_terminal() and node.untried_moves:
            # Sort moves by RL values
            rl_sorted_moves = []
            for move in node.untried_moves[:10]:  # Limit for performance
                rl_value = self._get_rl_move_value(node.board, move)
                priority = self.evaluator.get_move_priority(node.board, move)
                combined_score = priority + self.rl_weight * rl_value * 10
                rl_sorted_moves.append((move, combined_score))
            
            rl_sorted_moves.sort(key=lambda x: x[1], reverse=True)
            
            # Select best move for expansion
            if rl_sorted_moves:
                selected_move = rl_sorted_moves[0][0]
                node.untried_moves.remove(selected_move)
                
                new_board = node.board.copy()
                try:
                    success = self._make_move_safe(new_board, selected_move)
                    if success:
                        child = MCTSNode(new_board, selected_move, node)
                        node.children.append(child)
                        return child
                except Exception:
                    pass
        
        return node
    
    def _make_move_safe(self, board: ChessBoard, move: tuple) -> bool:
        """Safely make a move on the board"""
        try:
            if len(move) > 4:
                return board.make_move(move[0], move[1], move[2], move[3], move[4])
            else:
                return board.make_move(move[0], move[1], move[2], move[3])
        except Exception:
            return False
    
    def _get_rl_move_value(self, board: ChessBoard, move: tuple) -> float:
        """Get RL-based value estimation for a move"""
        # Simplified RL value estimation
        # In production, this would use a trained neural network
        value = 0
        
        from_row, from_col, to_row, to_col = move[:4]
        
        # Center control bonus
        if (to_row, to_col) in [(3, 3), (3, 4), (4, 3), (4, 4)]:
            value += 0.3
        elif (to_row, to_col) in [(2, 2), (2, 3), (2, 4), (2, 5), (3, 2), (3, 5), 
                                  (4, 2), (4, 5), (5, 2), (5, 3), (5, 4), (5, 5)]:
            value += 0.1
        
        # Development bonus
        piece = board.board[from_row][from_col]
        if piece and not piece.has_moved:
            if piece.type.value in ['N', 'B']:  # Knight or Bishop
                value += 0.2
        
        # Capture evaluation
        target = board.board[to_row][to_col]
        if target:
            piece_values = {'P': 0.1, 'N': 0.3, 'B': 0.3, 'R': 0.5, 'Q': 0.9}
            value += piece_values.get(target.type.value, 0)
        
        # King safety consideration
        if piece and piece.type.value == 'K':
            total_pieces = sum(1 for r in range(8) for c in range(8) if board.board[r][c])
            if total_pieces > 20:  # Opening/middlegame
                if 2 <= to_row <= 5 and 2 <= to_col <= 5:
                    value -= 0.4
        
        # Pattern recognition from position history
        if len(self.position_history) > 5:
            recent_positions = list(self.position_history)[-5:]
            for pos_data in recent_positions:
                if 'result' in pos_data:
                    result_value = pos_data['result']
                    if result_value == 'good':
                        value += 0.1
                    elif result_value == 'bad':
                        value -= 0.1
        
        return max(-1.0, min(1.0, value))
    
    def _rl_simulate(self, node: MCTSNode):
        """RL-enhanced simulation"""
        board = node.board.copy()
        simulation_moves = 0
        max_simulation_moves = 50
        
        while (not board.is_checkmate() and not board.is_stalemate() and 
               simulation_moves < max_simulation_moves):
            
            moves = board.get_all_legal_moves()
            if not moves:
                break
            
            move = self._rl_select_simulation_move(board, moves)
            if not move:
                break
            
            if not self._make_move_safe(board, move):
                break
            
            simulation_moves += 1
        
        return self._evaluate_final_position(board)
    
    def _rl_select_simulation_move(self, board: ChessBoard, moves: list):
        """Select simulation move with RL guidance"""
        if not moves:
            return None
        
        # Score moves with RL values
        move_scores = []
        for move in moves:
            priority = self.evaluator.get_move_priority(board, move)
            rl_value = self._get_rl_move_value(board, move)
            total_score = priority + self.rl_weight * rl_value * 5
            move_scores.append((move, total_score))
        
        move_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Weighted random selection
        top_count = max(1, len(move_scores) // 3)
        if random.random() < 0.7 and move_scores:
            return random.choice(move_scores[:top_count])[0]
        else:
            return random.choice(moves)
    
    def _rl_select_best_move(self, root: MCTSNode):
        """Select best move with RL enhancement"""
        if not root.children:
            return None
        
        best_child = None
        best_score = -float('inf')
        
        for child in root.children:
            if child.visits < 5:
                continue
            
            # Traditional evaluation
            win_rate = child.wins / child.visits
            visit_weight = min(child.visits / max(c.visits for c in root.children), 1.0)
            traditional_score = win_rate * 0.7 + visit_weight * 0.3
            
            # RL enhancement
            rl_value = self._get_rl_move_value(child.board, child.move)
            
            # Combined score
            total_score = traditional_score + self.rl_weight * rl_value
            
            if total_score > best_score:
                best_score = total_score
                best_child = child
        
        return best_child or root.most_visited_child()
    
    def _rl_fallback_move(self, board: ChessBoard, legal_moves: list):
        """Fallback move selection with RL"""
        if not legal_moves:
            return None
        
        move_scores = []
        for move in legal_moves:
            priority = self.evaluator.get_move_priority(board, move)
            rl_value = self._get_rl_move_value(board, move)
            total_score = priority + self.rl_weight * rl_value * 10
            move_scores.append((move, total_score))
        
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return move_scores[0][0]
    
    def record_game_outcome(self, result: str, final_board: ChessBoard):
        """Record the game outcome for RL learning"""
        if self.data_recorder and self.current_game_id:
            final_position = json.dumps(final_board.to_dict())
            self.data_recorder.finish_game_recording(
                self.current_game_id, result, final_position, self.move_number
            )
        
        # Update position history with results
        result_value = 'good' if 'wins' in result.lower() else 'bad' if 'loses' in result.lower() else 'neutral'
        for position in list(self.position_history)[-10:]:
            position['result'] = result_value
    
    def _simple_move_score(self, board: ChessBoard, move: tuple) -> float:
        """Simple move scoring without evaluator dependency"""
        score = 0.0
        from_row, from_col, to_row, to_col = move[:4]
        
        # Capture bonus
        target = board.board[to_row][to_col]
        if target:
            piece_values = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 100}
            score += piece_values.get(target.type.value, 0) * 10
        
        # Center control bonus
        if (to_row, to_col) in [(3, 3), (3, 4), (4, 3), (4, 4)]:
            score += 5
        elif 2 <= to_row <= 5 and 2 <= to_col <= 5:
            score += 2
        
        # Development bonus for pieces that haven't moved
        piece = board.board[from_row][from_col]
        if piece and not piece.has_moved:
            if piece.type.value in ['N', 'B']:
                score += 3
        
        # Add some randomness for variety
        score += random.random() * 0.5
        
        return score
