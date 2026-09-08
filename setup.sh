#!/bin/bash

# This file mostly written by Gemini.

# Exit immediately if a command exits with a non-zero status
set -e

# Color definitions (ANSI escape codes)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=== Starting GAAP Setup Script ==="

export ARRIVING_PATH="$PWD/"

SHOW_REMINDER=false

# -------------------------------------------------------------------------
# Step 2: Passive Environment Check
# -------------------------------------------------------------------------
if [ -z "$ARRIVING_PATH" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}[Warning]${NC} ARRIVING_PATH or OPENAI_API_KEY is not detected in this session yet."
    SHOW_REMINDER=true
fi

# -------------------------------------------------------------------------
# Steps 3 & 4: Verify Dependencies
# -------------------------------------------------------------------------
if ! command -v uv &> /dev/null; then
    echo -e "${RED}[Error]${NC} 'uv' is not installed. Please install it first." >&2
    exit 1
fi

if ! command -v sqlite3 &> /dev/null; then
    echo -e "${RED}[Error]${NC} 'sqlite3' is not installed. Please install it first." >&2
    exit 1
fi

# -------------------------------------------------------------------------
# Step 5: Initialize Added Databases
# -------------------------------------------------------------------------
echo "Configuring databases..."

if [ ! -f "internalData.db" ]; then
    sqlite3 internalData.db < agent_helpers/InternalSchema.sql
    echo -e "${GREEN}[Complete]${NC} Created internalData.db"
else
    echo -e "${CYAN}[Info]${NC} internalData.db already exists. Skipping initialization."
fi

if [ ! -f "queries_4.db" ]; then
    sqlite3 queries_4.db < operation_helpers/QueriesSchema.sql
    echo -e "${GREEN}[Complete]${NC} Created queries_4.db"
else
    echo -e "${CYAN}[Info]${NC} queries_4.db already exists. Skipping initialization."
fi

# -------------------------------------------------------------------------
# Step 6: Copy templates & Prompt for Private Data DB style
# -------------------------------------------------------------------------
echo "Copying template files..."

if [ ! -f "agent_helpers/database.py" ]; then
    cp agent_helpers/database_template.py agent_helpers/database.py
    echo -e "${GREEN}[Complete]${NC} Created agent_helpers/database.py"
else
    echo -e "${CYAN}[Info]${NC} agent_helpers/database.py already exists. Skipping copy."
fi

if [ ! -f "privateData.db" ]; then
    echo -e "${YELLOW}[Action]${NC} How would you like to initialize privateData.db?"
    echo "  1) Initialize a fresh, empty private data database (default)"
    echo "  2) Use the template with example baseline fields"
    read -p "Enter choice [1 or 2, default 1]: " db_choice

    # Defaults to option 1 if empty or explicitly set to 1
    if [ "$db_choice" = "2" ]; then
        cp privateData_template_filled.db privateData.db
        echo -e "${GREEN}[Complete]${NC} Created privateData.db from baseline template"
    else
         cp privateData_template.db privateData.db
	echo -e "${GREEN}[Complete]${NC} Initialized a fresh privateData.db"
    fi
else
    echo -e "${CYAN}[Info]${NC} privateData.db already exists. Skipping initialization."
fi

# -------------------------------------------------------------------------
# Step 8: Create directories
# -------------------------------------------------------------------------
echo "Creating required directories..."
mkdir -p editable_files
mkdir -p later_runs

# -------------------------------------------------------------------------
# Step 9: Verify LLM API Status
# -------------------------------------------------------------------------
echo "Running initial API test..."
if ! uv run -q external_modifications/initial_api_test.py; then
    echo -e "${RED}[Error]${NC} The LLM may not be working right." >&2
fi

# -------------------------------------------------------------------------
# Final Reminders
# -------------------------------------------------------------------------
echo ""
echo -e "${GREEN}[Complete] Setup finished${NC}"
if [ "$SHOW_REMINDER" = true ]; then
    echo -e "${YELLOW}[Reminder]${NC} Please ensure you set your environment variables in your terminal:"
    echo "   export <OPENAI or GEMINI>_API_KEY=\"<add-key-here>\""
fi
echo ""
echo -e "${CYAN}[Action]${NC} Run the interactive command line interface using:"
echo "   ./gaap_run.sh"
