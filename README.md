# MCTS Chess Engine

A modern chess engine implementation using Monte Carlo Tree Search (MCTS) algorithm, built with FastAPI backend and interactive HTML frontend.

## 📋 Prerequisites

- **uv** - Python package manager (recommended)
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Python 3.7+ (uv will handle this automatically)

## 🚀 Quick Start

### Option 1: Using the startup script (Recommended)
```bash
./run.sh
```

### Option 2: Manual setup with uv
```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Add dependencies from requirements.txt
uv add -r requirements.txt

# Run the application
uv run python main.py
```

### Option 3: Development mode (with hot reload)
```bash
# After initial setup
./dev.sh
```

## 🎮 Usage

1. Open your browser and go to `http://localhost:8000`
2. Play as White against the MCTS AI (Black)
3. Click pieces to select them, then click highlighted squares to move
4. The AI will automatically make its move after yours

## 📚 API Documentation

- **Game Interface**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### API Endpoints

- `GET /api/game/state` - Get current game state
- `POST /api/game/move` - Make a player move
- `POST /api/game/ai_move` - Get AI move using MCTS
- `POST /api/game/reset` - Reset the game

## 🧠 MCTS Algorithm

The engine uses Monte Carlo Tree Search with:
- **Time limit**: 3 seconds per move
- **Simulations**: ~500 per move
- **UCB1**: Upper Confidence Bound for tree traversal
- **Random playouts**: With capture preference

### MCTS Phases:
1. **Selection**: Navigate tree using UCB1 values
2. **Expansion**: Add new nodes to the tree
3. **Simulation**: Run random games to completion
4. **Backpropagation**: Update node statistics

## 🏗️ Project Structure

```
MCTs/
├── main.py              # FastAPI backend with MCTS engine
├── requirements.txt     # Python dependencies
├── run.sh              # Startup script
├── templates/
│   └── index.html      # Game interface
├── static/             # Static assets (if needed)
└── README.md          # This file
```

## 🔧 Configuration

You can modify the MCTS parameters in `main.py`:

```python
mcts_engine = ChessMCTS(
    time_limit=3.0,      # Seconds per move
    max_simulations=500   # Maximum simulations
)
```

## 🎯 Features

- ♟️ Full chess implementation with legal move validation
- 🤖 MCTS-based AI opponent
- 🎨 Modern, responsive web interface
- 📊 Real-time game statistics
- 🔄 Move history tracking
- ⚡ FastAPI backend with automatic API documentation
- 🎮 Interactive piece selection and move highlighting

## 🛠️ Development

The project uses:
- **Backend**: FastAPI, Python 3.7+
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **AI**: Monte Carlo Tree Search
- **Chess Logic**: Custom implementation

## 📈 Performance

- Average move calculation: 2-4 seconds
- Simulations per move: 300-800
- Memory usage: ~50MB
- Supports concurrent games (stateless API)

## 🤝 Contributing

Feel free to contribute improvements to:
- MCTS algorithm optimizations
- Chess engine enhancements
- UI/UX improvements
- Performance optimizations

## 📝 License

This project is for educational purposes. Feel free to use and modify as needed.
