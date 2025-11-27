#!/bin/bash

# Production startup script
# Starts the FastAPI backend with Gunicorn for production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "Installing gunicorn..."
    pip install gunicorn
fi

# Number of workers (2 * CPU cores + 1)
WORKERS=${WORKERS:-4}

echo "🚀 Starting FastAPI backend with Gunicorn..."
echo "   Workers: $WORKERS"
echo "   Host: 0.0.0.0"
echo "   Port: 8000"
echo ""

# Start with Gunicorn
exec gunicorn backend.main:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
