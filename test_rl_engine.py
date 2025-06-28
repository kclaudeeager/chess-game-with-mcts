#!/usr/bin/env python3
"""
Quick test script to verify RL engine works in isolation
"""

from models.chess_board import ChessBoard
from engines.rl_mcts import RLEnhancedMCTS

def test_rl_engine():
    # Create a chess board
    board = ChessBoard()
    
    # Make the exact same move as the session
    board.make_move(6, 4, 5, 4)  # e2e3
    print(f"Current player: {board.current_player}")
    legal_moves = board.get_all_legal_moves()
    print(f"Legal moves: {len(legal_moves)}")
    print(f"First few legal moves: {legal_moves[:3]}")
    
    # Create RL engine with exact same settings as session
    rl_engine = RLEnhancedMCTS(
        time_limit=6.0,
        max_simulations=3000,
        max_depth=40,
        rl_weight=0.3,
        data_recorder=None
    )
    
    # Test search
    print("Testing RL engine search...")
    try:
        move = rl_engine.search(board)
        print(f"RL engine returned: {move}")
        print(f"Move type: {type(move)}")
        
        if move:
            print(f"Move details: from ({move[0]},{move[1]}) to ({move[2]},{move[3]})")
            print(f"Move length: {len(move)}")
        else:
            print("No move returned!")
            
    except Exception as e:
        print(f"Error in RL engine: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error str: '{str(e)}'")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rl_engine()
