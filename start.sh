#!/usr/bin/env bash
# ==============================================================================
# Apple Notes MCP & FastAPI Swagger Server Runner
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Ensure venv exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment using uv..."
    if command -v uv >/dev/null 2>&1; then
        uv venv .venv --python 3.12
        uv pip install -r requirements.txt
    elif [ -x "/opt/homebrew/bin/uv" ]; then
        /opt/homebrew/bin/uv venv .venv --python 3.12
        /opt/homebrew/bin/uv pip install -r requirements.txt
    else
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt
    fi
fi

export PYTHONPATH="$DIR:$PYTHONPATH"
PYTHON_BIN="$DIR/.venv/bin/python3"

MODE="${1:-api}"

if [ "$MODE" = "mcp" ]; then
    echo "=========================================================="
    echo "🚀 Starting Apple Notes MCP Server (stdio transport)..."
    echo "   Ready to handle tool requests from AI MCP clients."
    echo "=========================================================="
    exec "$PYTHON_BIN" "$DIR/mcp_server.py" --transport stdio
elif [ "$MODE" = "test" ]; then
    echo "=========================================================="
    echo "🧪 Running Automated Test Suite..."
    echo "=========================================================="
    exec "$PYTHON_BIN" -m pytest "$DIR/tests" -v
else
    PORT="${PORT:-8000}"
    HOST="${HOST:-127.0.0.1}"
    echo "=========================================================="
    echo "🚀 Starting Apple Notes REST API & Swagger UI Server"
    echo "   📍 Interactive Swagger UI:  http://$HOST:$PORT/docs"
    echo "   📍 ReDoc Documentation:     http://$HOST:$PORT/redoc"
    echo "   📍 OpenAPI Specification:   http://$HOST:$PORT/openapi.json"
    echo "   📍 Web Dashboard:           http://$HOST:$PORT/"
    echo "=========================================================="
    exec "$PYTHON_BIN" -m uvicorn api:app --host "$HOST" --port "$PORT"
fi
