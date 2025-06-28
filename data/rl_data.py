"""
RL data recording and storage for training chess engines.
"""
import sqlite3
import time
import uuid
from threading import Lock
from typing import Dict, Optional


class GameDataRecorder:
    """Records game data for RL training"""
    
    def __init__(self, db_path: str = "chess_games.db"):
        self.db_path = db_path
        self.data_lock = Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing game data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Games table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    game_id TEXT UNIQUE,
                    game_mode TEXT,
                    start_time REAL,
                    end_time REAL,
                    result TEXT,
                    final_position TEXT,
                    total_moves INTEGER
                )
            ''')
            
            # Positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT,
                    move_number INTEGER,
                    position TEXT,
                    player TEXT,
                    move_made TEXT,
                    evaluation REAL,
                    timestamp REAL,
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_session ON games(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_game ON positions(game_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_move ON positions(move_number)')
            
            conn.commit()
    
    def start_game_recording(self, session_id: str, game_mode: str) -> str:
        """Start recording a new game"""
        with self.data_lock:
            game_id = str(uuid.uuid4())
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO games (session_id, game_id, game_mode, start_time)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, game_id, game_mode, current_time))
                conn.commit()
            
            return game_id
    
    def record_position(self, position_data: Dict):
        """Record a position and associated data"""
        with self.data_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO positions 
                    (game_id, move_number, position, player, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    position_data.get('game_id'),
                    position_data.get('move_number', 0),
                    position_data.get('position', ''),
                    position_data.get('player', ''),
                    time.time()
                ))
                conn.commit()
    
    def record_move(self, game_id: str, move_number: int, move_data: str, evaluation: float = 0.0):
        """Record a move made in the game"""
        with self.data_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE positions 
                    SET move_made = ?, evaluation = ?
                    WHERE game_id = ? AND move_number = ?
                ''', (move_data, evaluation, game_id, move_number))
                conn.commit()
    
    def finish_game_recording(self, game_id: str, result: str, final_position: str, total_moves: int):
        """Finish recording a game with final result"""
        with self.data_lock:
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE games 
                    SET end_time = ?, result = ?, final_position = ?, total_moves = ?
                    WHERE game_id = ?
                ''', (current_time, result, final_position, total_moves, game_id))
                conn.commit()
    
    def get_game_data(self, game_id: str) -> Optional[Dict]:
        """Get complete game data including all positions"""
        with self.data_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get game info
                cursor.execute('SELECT * FROM games WHERE game_id = ?', (game_id,))
                game_row = cursor.fetchone()
                
                if not game_row:
                    return None
                
                # Get all positions
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE game_id = ? 
                    ORDER BY move_number
                ''', (game_id,))
                position_rows = cursor.fetchall()
                
                # Format data
                game_data = {
                    'game_id': game_row[2],
                    'session_id': game_row[1],
                    'game_mode': game_row[3],
                    'start_time': game_row[4],
                    'end_time': game_row[5],
                    'result': game_row[6],
                    'final_position': game_row[7],
                    'total_moves': game_row[8],
                    'positions': []
                }
                
                for row in position_rows:
                    position_data = {
                        'move_number': row[2],
                        'position': row[3],
                        'player': row[4],
                        'move_made': row[5],
                        'evaluation': row[6],
                        'timestamp': row[7]
                    }
                    game_data['positions'].append(position_data)
                
                return game_data
    
    def get_recent_games(self, limit: int = 100) -> list:
        """Get recent games for analysis"""
        with self.data_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT game_id, session_id, game_mode, result, total_moves, start_time
                    FROM games 
                    WHERE end_time IS NOT NULL
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                games = []
                
                for row in rows:
                    game_info = {
                        'game_id': row[0],
                        'session_id': row[1],
                        'game_mode': row[2],
                        'result': row[3],
                        'total_moves': row[4],
                        'start_time': row[5]
                    }
                    games.append(game_info)
                
                return games
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with self.data_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total games
                cursor.execute('SELECT COUNT(*) FROM games')
                total_games = cursor.fetchone()[0]
                
                # Completed games
                cursor.execute('SELECT COUNT(*) FROM games WHERE end_time IS NOT NULL')
                completed_games = cursor.fetchone()[0]
                
                # Total positions
                cursor.execute('SELECT COUNT(*) FROM positions')
                total_positions = cursor.fetchone()[0]
                
                # Game results distribution
                cursor.execute('''
                    SELECT result, COUNT(*) 
                    FROM games 
                    WHERE result IS NOT NULL 
                    GROUP BY result
                ''')
                results_distribution = dict(cursor.fetchall())
                
                return {
                    'total_games': total_games,
                    'completed_games': completed_games,
                    'total_positions': total_positions,
                    'results_distribution': results_distribution
                }
    
    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old game data"""
        with self.data_lock:
            cutoff_time = time.time() - (days_old * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get old game IDs
                cursor.execute('''
                    SELECT game_id FROM games 
                    WHERE start_time < ?
                ''', (cutoff_time,))
                old_game_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete positions for old games
                for game_id in old_game_ids:
                    cursor.execute('DELETE FROM positions WHERE game_id = ?', (game_id,))
                
                # Delete old games
                cursor.execute('DELETE FROM games WHERE start_time < ?', (cutoff_time,))
                
                conn.commit()
                
                return len(old_game_ids)
    
    def record_game(self, board_state: dict, move_sequence: list, player_won: bool, game_result: str):
        """Record a completed game for RL training"""
        try:
            with self.data_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Insert game record
                    game_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO games (game_id, session_id, game_mode, start_time, end_time, result, final_position, total_moves)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        game_id, 
                        game_id,  # Use game_id as session_id for now
                        'human_vs_ai',
                        time.time() - 300,  # Approximate start time
                        time.time(),
                        game_result,
                        str(board_state),
                        len(move_sequence)
                    ))
                    
                    print(f"📊 Recorded RL game data: {game_result}")
                    
        except Exception as e:
            print(f"❌ Error recording game: {e}")
    
    def get_total_entries(self) -> int:
        """Get total number of recorded games"""
        try:
            with self.data_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM games')
                    return cursor.fetchone()[0]
        except Exception as e:
            print(f"❌ Error getting total entries: {e}")
            return 0
