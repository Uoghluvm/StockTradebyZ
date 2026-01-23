#!/bin/bash

# ========================================================
# StockTrade Daily Automation Script
# Schedule with crontab: 0 15 * * 1-5 /path/to/this/script.sh
# ========================================================

# 1. Initialize Environment
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Go to project root
cd "$PROJECT_ROOT"

echo "========================================================"
echo "Starting Daily Job: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo "========================================================"

# Try to find python
# Prefer the one from .env if defined, or system python
# Assuming standard setup: python is in PATH or this script is run via a wrapper
# For robustness, we try to source conda if available, or just use 'python'
# You might need to edit this line to point to your specific python executable
# e.g., PYTHON_EXE="/Users/username/anaconda3/envs/stock/bin/python"
PYTHON_EXE="python" 

# Check if we can find python
if ! command -v "$PYTHON_EXE" &> /dev/null; then
    echo "Error: '$PYTHON_EXE' could not be found. Please edit this script to set PYTHON_EXE."
    exit 1
fi

# 2. Daily Data Fetch (K-Line)
echo "[1/2] Fetching latest K-line data..."
$PYTHON_EXE scripts/fetch_kline.py
if [ $? -ne 0 ]; then
    echo "❌ Fetch failed."
    # We continue anyway to try selection on existing data? No, usually heavy fail.
    # exit 1
else
    echo "✅ Fetch complete."
fi

# 3. Process Stock Selection for Today
TODAY=$(date +%Y-%m-%d)
echo "[2/2] Running Stock Selection for $TODAY..."

# Check if today is a weekday (Script runs via cron 1-5, but double check doesn't hurt)
# select_stock.py handles logic
$PYTHON_EXE scripts/select_stock.py --date "$TODAY"

if [ $? -ne 0 ]; then
    echo "❌ Selection failed."
else
    echo "✅ Selection complete."
    
    # Optional: Run Backtest immediately if we have data for today (usually only Open price is needed for T+0 sim or T+1)
    # But real backtest needs Future data. So we skip backtest for "Today".
    # ----------------------------------------------------
    # 4. Check for "Golden Combinations" (Alert Logic)
    # ----------------------------------------------------
    LOG_FILE="logs/${TODAY}选股.csv"
    
    if [ -f "$LOG_FILE" ]; then
        # Check for specific strategy combinations with loose matching
        # Combinations: "少妇战法+填坑战法+上穿60放量战法" or subsets
        
        # Grep returns 0 if found
        # Using -E for extended regex or multiple patterns
        # Note: The CSV might have them in any order or combined string. 
        # Usually they appear in 'strategies' column like "strategyA,strategyB" or "strategyA+strategyB"
        
        FOUND_GOLD=0
        MATCHED_LINES=""
        
        # Pattern 1: 少妇 + 填坑 + 上穿60
        if grep -q "少妇战法.*填坑战法.*上穿60放量战法" "$LOG_FILE" || \
           grep -q "填坑战法.*少妇战法.*上穿60放量战法" "$LOG_FILE" || \
           grep -q "上穿60放量战法.*少妇战法.*填坑战法" "$LOG_FILE"; then
           FOUND_GOLD=1
        fi
        
        # Pattern 2: 少妇 + 上穿60
        if grep -q "少妇战法.*上穿60放量战法" "$LOG_FILE" || grep -q "上穿60放量战法.*少妇战法" "$LOG_FILE"; then
           FOUND_GOLD=1
        fi

        # Pattern 3: 填坑 + 上穿60
        if grep -q "填坑战法.*上穿60放量战法" "$LOG_FILE" || grep -q "上穿60放量战法.*填坑战法" "$LOG_FILE"; then
           FOUND_GOLD=1
        fi
        
        if [ $FOUND_GOLD -eq 1 ]; then
            echo ""
            echo "🔥 🔥 🔥 SUPER SIGNAL ALERT 🔥 🔥 🔥"
            echo "Found Golden Strategy Combination in $LOG_FILE!"
            echo "Combinations found:"
            
            # Print matching lines for quick review
            grep "上穿60放量战法" "$LOG_FILE" | grep -E "少妇战法|填坑战法"
            
            echo ""
            
            # Send macOS Notification (if running on Mac)
            if command -v osascript &> /dev/null; then
                osascript -e 'display notification "🔥StockTrade: Found Golden Strategy Combination!" with title "Super Signal Alert" sound name "Ping"'
            fi
            
            # Terminal Bell
            echo -e "\a"
        else
            echo "No Golden Combinations found today."
        fi
    else
        echo "⚠️ Log file not found: $LOG_FILE"
    fi
fi

echo "Job finished at $(date)"
echo "========================================================"
echo ""
