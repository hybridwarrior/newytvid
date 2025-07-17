#!/bin/bash
# Quick test script to verify webhook works

echo "=== Testing Dropbox Webhook Setup ==="

# Change to project directory
cd /opt/new-yt

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt

# Start webhook server in test mode
echo ""
echo "Starting webhook server for testing..."
echo "This will run on port 8080"
echo ""
echo "To test locally:"
echo "  curl http://localhost:8080/webhook?challenge=test"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with host 0.0.0.0 for testing
WEBHOOK_HOST=0.0.0.0 python scripts/webhook_server.py