#!/bin/bash

# MCTS Chess Engine - Ngrok Setup Script

echo "🌐 Setting up MCTS Chess Engine with Ngrok"
echo "=========================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ Ngrok is not installed."
    echo "📦 Install ngrok from: https://ngrok.com/download"
    echo "   Or use: brew install ngrok (on macOS)"
    exit 1
fi

# Check if the server is running locally
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ MCTS Chess server is not running on localhost:8000"
    echo "🚀 Please start the server first with: ./run.sh"
    exit 1
fi

echo "✅ Local server is running"
echo "🌐 Starting ngrok tunnel..."

# Start ngrok and capture the URL
echo ""
echo "📋 Ngrok will create a public URL for your chess game"
echo "🔗 Share this URL with others to play online!"
echo ""
echo "⚠️  Note: The free ngrok plan has session limits"
echo ""

# Start ngrok
ngrok http 8000
