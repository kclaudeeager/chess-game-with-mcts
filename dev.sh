#!/bin/bash

# Quick development run (assumes dependencies are already installed)

echo "🚀 Starting MCTS Chess Engine (Development Mode)..."
echo "   Game URL: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""

# Start with hot reload enabled
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
