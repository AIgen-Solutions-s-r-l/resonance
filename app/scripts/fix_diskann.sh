#!/bin/bash
# Script to fix diskann index issues
# Usage: ./fix_diskann.sh [upgrade|reindex|recreate] [--force]

# Set default mode
MODE="upgrade"
FORCE=""

# Parse arguments
if [ "$1" == "upgrade" ] || [ "$1" == "reindex" ] || [ "$1" == "recreate" ]; then
    MODE="$1"
    shift
fi

if [ "$1" == "--force" ]; then
    FORCE="--force"
fi

# Display header
echo "========================================"
echo "DiskANN Index Fix Tool"
echo "========================================"
echo "Mode: $MODE"
if [ "$FORCE" == "--force" ]; then
    echo "Force: Yes (no confirmations)"
else
    echo "Force: No (will ask for confirmation)"
fi
echo "========================================"

# Determine the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the appropriate script
echo "Running fix script..."
if [ "$MODE" == "upgrade" ] && [ "$FORCE" == "" ]; then
    python -m app.scripts.upgrade_diskann_index
else
    python -m app.scripts.fix_diskann_index --mode="$MODE" $FORCE
fi

# Check exit status
if [ $? -eq 0 ]; then
    echo "========================================"
    echo "Fix completed successfully!"
    echo "========================================"
    
    if [ "$MODE" == "recreate" ]; then
        echo "You need to recreate the indices now."
        echo "Run: python -m app.scripts.create_vector_indices"
        
        # Ask if user wants to recreate indices now
        if [ "$FORCE" == "" ]; then
            read -p "Do you want to recreate indices now? (y/n): " RECREATE
            if [ "$RECREATE" == "y" ] || [ "$RECREATE" == "Y" ]; then
                echo "Recreating indices..."
                python -m app.scripts.create_vector_indices --force
            fi
        fi
    fi
else
    echo "========================================"
    echo "Fix failed! Check the logs for details."
    echo "========================================"
    exit 1
fi

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate 2>/dev/null || true
fi

echo "Done."