#!/bin/bash

# MCTS Chess Engine Startup Script

echo "🎯 MCTS Chess Engine Setup with UV"
echo "==================================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ UV is required but not installed."
    echo "📦 Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Add dependencies from requirements.txt if pyproject.toml doesn't have them
if [ -f "requirements.txt" ] && [ ! -f ".dependencies_added" ]; then
    echo "📚 Adding dependencies from requirements.txt..."
    uv add -r requirements.txt
    touch .dependencies_added
fi

# Sync dependencies (this will install from pyproject.toml)
echo "� Syncing dependencies with uv..."
uv sync

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting MCTS Chess Engine..."
echo "   Game URL: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
uv run python main.py
