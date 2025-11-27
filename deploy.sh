#!/bin/bash

# Deployment script for Hybrid RAG Application
# This script builds the frontend and sets up the application for Nginx

set -e

echo "🚀 Starting deployment..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Build Frontend
echo -e "${YELLOW}📦 Building frontend...${NC}"
cd frontend
npm install
npm run build
cd ..
echo -e "${GREEN}✅ Frontend built successfully${NC}"

# Step 2: Setup Python virtual environment
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet
python -c "import nltk; nltk.download('stopwords', quiet=True)" 2>/dev/null || true
python -m spacy download en_core_web_sm --quiet 2>/dev/null || true
echo -e "${GREEN}✅ Python environment ready${NC}"

# Step 3: Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}🍎 Detected macOS${NC}"
    NGINX_CONF_DIR="/usr/local/etc/nginx"
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}❌ Nginx not installed. Install with: brew install nginx${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}🐧 Detected Linux${NC}"
    NGINX_CONF_DIR="/etc/nginx"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps to complete deployment:${NC}"
echo ""
echo "1. Start the FastAPI backend:"
echo "   source venv/bin/activate"
echo "   uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "2. Configure Nginx:"
echo ""
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   For macOS (local testing on port 8080):"
    echo "   sudo nginx -c $SCRIPT_DIR/nginx/nginx.local.conf"
    echo ""
    echo "   Or copy config to Nginx directory:"
    echo "   sudo cp nginx/nginx.local.conf $NGINX_CONF_DIR/nginx.conf"
    echo "   sudo nginx"
else
    echo "   For Linux production:"
    echo "   sudo cp nginx/nginx.conf /etc/nginx/nginx.conf"
    echo "   sudo systemctl restart nginx"
fi
echo ""
echo "3. Access the application:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   http://localhost:8080"
else
    echo "   http://localhost"
fi
echo ""
echo "4. API documentation:"
echo "   http://localhost:8000/docs"
echo ""
