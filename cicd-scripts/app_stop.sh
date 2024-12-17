#!/bin/bash

chmod +x ./cicd-scripts/helpers/ensure_executable.sh
source ./cicd-scripts/helpers/ensure_executable.sh

### FUNCTIONS ###

# Remove virtual environment if it exists
remove_venv() {
    if [ -d ./venv ]; then
        echo "Removing virtual environment..."
        rm -rf ./venv/
    fi
}

# Purge pip cache
purge_pip_cache() {
    echo "Purging pip cache..."
    rm -rf ~/.cache/pip /root/.cache/pip
}

# Stop scrapy scheduler if running
stop_scrapy_scheduler() {
    echo "Stopping scrapy_scheduler.py (if running)..."
    ensure_executable "./cicd-scripts/helpers/kill_scheduler.sh"
}

# Stop scrapyd and scrapydweb tasks
stop_scrapy_tasks() {
    echo "Stopping all scrapyd and scrapydweb tasks..."

    # Kill scrapydweb tasks
    if pkill -f "scrapydweb" 2>/dev/null; then
        echo "scrapydweb tasks stopped."
    else
        echo "No scrapydweb tasks running."
    fi

    # Kill scrapyd tasks
    if pkill -f "scrapyd" 2>/dev/null; then
        echo "scrapyd tasks stopped."
    else
        echo "No scrapyd tasks running."
    fi
}

# Display remaining scrapy processes
display_remaining_scrapy_processes() {
    echo -e "\nRemaining scrapy processes (if any):"
    ps -ef | grep scrapy | grep -v grep || echo "No scrapy processes running."
}

# Force kill any remaining scrapy background jobs
kill_remaining_scrapy_jobs() {
    echo "Force killing remaining scrapy background jobs..."
    if ps aux | grep -ie [s]crapy | awk '{print $2}' | xargs kill -9; then
        echo "Remaining scrapy jobs killed."
    else
        echo "No remaining scrapy jobs to kill."
    fi
}

# Remove nohup jobs (python scripts)
remove_nohup_jobs() {
    echo "Removing nohup jobs (python)..."
    ps -ef | grep nohup | grep -v grep | awk '{print $2}' | xargs kill -9
}

# Remove cron job entries referencing the given string
remove_cron_entry() {
    if [ -z "$1" ]; then
        echo "Error: No cron entry provided."
        return
    fi

    local CRON_ENTRY="$1"
    local CRON_USER=$(whoami)

    echo "Removing cron job entries referencing: $CRON_ENTRY"

    # Remove cron job for the current user (including the full path if needed)
    sudo crontab -l -u "$CRON_USER" 2>/dev/null | grep -v -F "$CRON_ENTRY" | sudo crontab -u "$CRON_USER" -

    echo "Cron job entries for '$CRON_ENTRY' removed."
}

### SCRIPT EXECUTION ###

# Remove virtual environment
remove_venv

# Purge pip cache
purge_pip_cache

# Stop scrapy scheduler if running
stop_scrapy_scheduler

# Stop scrapyd and scrapydweb tasks
stop_scrapy_tasks

# Display remaining scrapy processes (if any)
display_remaining_scrapy_processes

# Force kill any remaining scrapy background jobs
kill_remaining_scrapy_jobs

# Remove nohup jobs (python)
remove_nohup_jobs

# Remove specific cron jobs
remove_cron_entry "check_cloudwatch.sh"
remove_cron_entry "check_codedeploy.sh"
remove_cron_entry "app_start.sh"

echo "App stop completed successfully."
