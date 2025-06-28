#!/bin/bash

# NgRok Setup Script for MCTS Chess Engine

echo "🌐 MCTS Chess Engine - NgRok Setup"
echo "=================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ NgRok is not installed."
    echo "📦 Install ngrok:"
    echo "   • Visit: https://ngrok.com/download"
    echo "   • Or use snap: sudo snap install ngrok"
    echo "   • Or use brew: brew install ngrok"
    exit 1
fi

# Check if the FastAPI server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ FastAPI server is not running on localhost:8000"
    echo "🚀 Please start the server first:"
    echo "   ./run.sh"
    echo ""
    echo "Or run in another terminal:"
    echo "   cd /home/claude/Documents/Study/MCTs"
    echo "   source .venv/bin/activate && uv run python main.py"
    exit 1
fi

echo "✅ FastAPI server is running on localhost:8000"
echo ""

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
echo "📝 This will:"
echo "   • Create a public URL for your local server"
echo "   • Allow access from anywhere on the internet"
echo "   • The frontend will automatically detect the ngrok URL"
echo ""

# Start ngrok and capture the URL
echo "🔗 Starting ngrok tunnel to localhost:8000..."
echo "   Press Ctrl+C to stop the tunnel"
echo ""

ngrok http 8000
