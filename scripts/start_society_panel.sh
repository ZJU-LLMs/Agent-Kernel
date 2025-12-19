#!/usr/bin/env bash

################################################################################
#                                                                              #
#                    SOCIETY-PANEL Unified Startup Script                      #
#                           (macOS/Linux Version)                              #
#                                                                              #
################################################################################
#
# Description:
#   This script automates the setup and launch of both the backend and frontend
#   services for the SOCIETY-PANEL. It handles dependency checks, virtual 
#   environment management, and graceful shutdown.
#
# Usage:
#   ./start_society_panel.sh
#
# Requirements:
#   - Python 3.11 or higher
#   - Node.js and npm
#   - Internet connection (for package installation)
#
# Author:  SOCIETY-PANEL Team
# Version: 3.0
#
################################################################################

# ==============================================================================
# Shell Options
# ==============================================================================

set -e          # Exit immediately if a command exits with a non-zero status
set -o pipefail # Exit if any command in a pipeline fails

# ==============================================================================
# Global Configuration
# ==============================================================================

# Directory Paths
readonly ROOT_DIR="$(pwd)"
readonly BACKEND_DIR="society-panel/backend"
readonly FRONTEND_DIR="society-panel/frontend"

# Server Ports
readonly BACKEND_PORT=8001
readonly FRONTEND_PORT=5174

# Python Version Requirements
readonly REQUIRED_PYTHON_MAJOR=3
readonly REQUIRED_PYTHON_MINOR=11

# PyPI Mirror Configuration (Chinese mirror for faster downloads)
readonly PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
readonly PIP_TRUSTED_HOST="mirrors.aliyun.com"

# Terminal Color Codes
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'  # No Color

# Process Tracking Variables
BACKEND_PID=""
FRONTEND_PID=""

# ==============================================================================
# Utility Functions
# ==============================================================================

##
# @brief Print an info message with green [INFO] prefix
# @param $1 Message to print
##
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

##
# @brief Print a warning message with yellow [WARN] prefix
# @param $1 Message to print
##
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

##
# @brief Print an error message with red [ERROR] prefix
# @param $1 Message to print
##
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

##
# @brief Find a suitable Python interpreter (>= 3.11)
# @return Echoes the Python command name if found, returns 1 if not found
##
find_python() {
    local candidates=("python3.11" "python3.12" "python3")
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            local version_output
            version_output=$("$cmd" --version 2>&1)
            local major minor
            major=$(echo "$version_output" | sed -E 's/Python ([0-9]+)\..*/\1/')
            minor=$(echo "$version_output" | sed -E 's/Python [0-9]+\.([0-9]+).*/\1/')
            # Added check: "$minor" -lt 13 to exclude Python 3.13
            if [[ "$major" -ge "$REQUIRED_PYTHON_MAJOR" && "$minor" -ge "$REQUIRED_PYTHON_MINOR" && "$minor" -lt 13 ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

##
# @brief Gracefully shutdown all services and cleanup resources
# @details Handles SIGINT and SIGTERM signals to ensure proper cleanup
##
cleanup() {
    print_info "Caught exit signal. Shutting down all services..."

    # Terminate backend process
    if [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" > /dev/null 2>&1; then
        print_info "Backend service (PID: $BACKEND_PID) has been sent a shutdown signal."
    fi

    # Terminate frontend process
    if [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" > /dev/null 2>&1; then
        print_info "Frontend service (PID: $FRONTEND_PID) has been sent a shutdown signal."
    fi

    sleep 1

    # Shutdown Ray cluster if running
    if ray status > /dev/null 2>&1; then
        print_info "Shutting down Ray cluster..."
        ray stop
        print_info "Ray cluster has been shut down."
    fi

    echo "Cleanup complete!"
    exit 0
}

# Register signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# ==============================================================================
# Pre-cleanup: Stop Lingering Services
# ==============================================================================

print_info "Performing pre-cleanup to stop any lingering services..."

# Kill any processes occupying the required ports
lsof -ti :"$BACKEND_PORT" | xargs kill -9 > /dev/null 2>&1 || true
lsof -ti :"$FRONTEND_PORT" | xargs kill -9 > /dev/null 2>&1 || true

# Stop Ray cluster if running
if ray status > /dev/null 2>&1; then
    ray stop
fi

print_info "Pre-cleanup finished."

# ==============================================================================
# Clean Workspace and Logs
# ==============================================================================

print_info "Cleaning backend workspace and logs directories..."

# Clean entire workspace directory contents
if [ -d "$BACKEND_DIR/workspace" ]; then
    rm -rf "$BACKEND_DIR/workspace"/*
    print_info "  - Cleaned: workspace/"
fi

# Clean backend logs directory (including all subdirectories)
if [ -d "$BACKEND_DIR/logs" ]; then
    find "$BACKEND_DIR/logs" -mindepth 1 -delete
    # Recreate subdirectory structure
    mkdir -p "$BACKEND_DIR/logs/framework" "$BACKEND_DIR/logs/app"
    print_info "  - Cleaned: logs/ (framework/, app/)"
fi

print_info "Workspace and logs cleanup finished."

# ==============================================================================
# Backend Service Setup and Launch
# ==============================================================================

print_info "Preparing backend service..."
cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

# Find and validate Python version
PYTHON_CMD=$(find_python) || {
    print_error "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ is required but not found!"
    print_error "Please install Python 3.11 or higher:"
    print_error "  macOS: brew install python@3.12"
    print_error "  Ubuntu: sudo apt install python3.12"
    exit 1
}
print_info "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# Create or activate virtual environment
if [ ! -d ".venv" ]; then
    print_warn "Backend virtual environment not found. Creating with $PYTHON_CMD..."
    "$PYTHON_CMD" -m venv .venv
    source .venv/bin/activate
    # Install certifi first to fix SSL certificate issues on macOS
    print_info "Installing SSL certificates (certifi)..."
    pip install --trusted-host "$PIP_TRUSTED_HOST" -i "$PIP_INDEX_URL" certifi
else
    source .venv/bin/activate
fi

# Configure SSL certificate path if certifi is installed
CERTIFI_PATH=$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null) || true
if [[ -n "$CERTIFI_PATH" ]]; then
    export SSL_CERT_FILE="$CERTIFI_PATH"
    export REQUESTS_CA_BUNDLE="$CERTIFI_PATH"
fi

# Install/update backend dependencies
if [ ! -f ".venv/pip_installed_reqs" ] || ! cmp -s "requirements.txt" ".venv/pip_installed_reqs"; then
    print_info "Upgrading pip to latest version..."
    pip install --trusted-host "$PIP_TRUSTED_HOST" -i "$PIP_INDEX_URL" --upgrade pip
    print_info "Backend dependencies need to be installed/updated. Running pip install..."
    pip install --trusted-host "$PIP_TRUSTED_HOST" -i "$PIP_INDEX_URL" -r requirements.txt && cp requirements.txt .venv/pip_installed_reqs
fi

# Launch backend server
print_info "Starting FastAPI backend in the background (Port: $BACKEND_PORT)..."
uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!
cd - > /dev/null

# ==============================================================================
# Frontend Service Setup and Launch
# ==============================================================================

print_info "Preparing frontend service..."
cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

# Install/update frontend dependencies
if [ ! -d "node_modules" ] || [ "package.json" -nt "package-lock.json" ]; then
    print_info "Frontend dependencies need to be installed or updated. Running npm install..."
    npm install
fi

# Launch frontend dev server
print_info "Starting Vite frontend dev server in the background (Port: $FRONTEND_PORT)..."
npm run dev -- --port "$FRONTEND_PORT" --host &
FRONTEND_PID=$!
cd - > /dev/null

# ==============================================================================
# Startup Complete - Wait for Termination
# ==============================================================================

print_info "=================================================="
print_info "SOCIETY-PANEL has been launched!"
print_info "  - Backend API available at: http://localhost:$BACKEND_PORT"
print_info "  - Frontend UI accessible at: http://localhost:$FRONTEND_PORT"
print_info "Press Ctrl+C to shut down all services."
print_info "=================================================="

wait
