#!/usr/bin/env python3
"""
Simple test to isolate the chess board issue
"""

print("Starting test...")

try:
    print("Importing enums...")
    from enum import Enum
    
    print("Creating Color enum...")
    class Color(Enum):
        WHITE = "white"
        BLACK = "black"
    
    print("Creating PieceType enum...")
    class PieceType(Enum):
        PAWN = "P"
        ROOK = "R"
        KNIGHT = "N" 
        BISHOP = "B"
        QUEEN = "Q"
        KING = "K"
    
    print("Creating Piece class...")
    class Piece:
        def __init__(self, type, color, has_moved=False):
            self.type = type
            self.color = color
            self.has_moved = has_moved
    
    print("Creating minimal ChessBoard...")
    class ChessBoard:
        def __init__(self):
            print("  Initializing board...")
            self.board = [[None for _ in range(8)] for _ in range(8)]
            print("  Setting current player...")
            self.current_player = Color.WHITE
            print("  Setting kings...")
            self.kings = {Color.WHITE: (7, 4), Color.BLACK: (0, 4)}
            print("  Done with init!")
    
    print("Creating board instance...")
    board = ChessBoard()
    print("SUCCESS! Board created successfully!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
