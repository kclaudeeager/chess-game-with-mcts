#!/usr/bin/env python3

import sys
import traceback

try:
    from models.chess_board import ChessBoard
    print("Successfully imported ChessBoard")
    
    board = ChessBoard()
    print("Successfully created board")
    
    legal_moves = board.get_all_legal_moves()
    print(f"Successfully got {len(legal_moves)} legal moves")
    
    # Test a few basic methods
    print(f"Current player: {board.current_player}")
    print(f"Is in check: {board.is_in_check(board.current_player)}")
    
    print("All tests passed!")
    
except Exception as e:
    print(f"Error occurred: {e}")
    print("Full traceback:")
    traceback.print_exc()
