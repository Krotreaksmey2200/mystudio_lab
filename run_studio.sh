#!/bin/bash
# TrainStudio AI - Startup Script

echo "=================================================="
echo "⚡ Starting TrainStudio AI (24/7 Training Engine)"
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3.10+."
    exit 1
fi

# Ensure in script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Install requirements if needed
echo "📦 Checking dependencies..."
python3 -m pip install -q -r requirements.txt

# Start FastAPI server on port 8000
echo "🚀 Launching Web Dashboard at: http://127.0.0.1:8000"
echo "🌐 Open your browser and go to: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop the web server."
echo "=================================================="

python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
