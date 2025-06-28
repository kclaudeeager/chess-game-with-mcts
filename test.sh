#!/bin/bash

# Test script to verify the MCTS Chess setup

echo "🧪 Testing MCTS Chess Engine Setup"
echo "==================================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ UV not found. Please install uv first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./run.sh first."
    exit 1
fi

# Activate and test imports
echo "🔍 Testing Python imports..."
source .venv/bin/activate

uv run python -c "
import fastapi
import uvicorn
import jinja2
import aiofiles
print('✅ All imports successful!')
print(f'FastAPI version: {fastapi.__version__}')
print(f'Uvicorn version: {uvicorn.__version__}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup test passed!"
    echo "🚀 Ready to run: ./run.sh or ./dev.sh"
else
    echo "❌ Setup test failed!"
    exit 1
fi
