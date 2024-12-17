#!/bin/bash
echo "###" $(pwd)
chmod +x ./cicd-scripts/helpers/ensure_executable.sh
./cicd-scripts/helpers/ensure_executable.sh

# TODO: Make it part of the local env variable that is set by Ansible
SPIDER_RUN_WITH_UI=false

# Determine which script to run based on the SPIDER_RUN_WITH_UI flag
if $SPIDER_RUN_WITH_UI; then
    SCRIPT="./cicd-scripts/helpers/run_with_ui.sh"
else
    SCRIPT="./cicd-scripts/helpers/run_without_ui.sh"
fi

# Ensure the script exists, is executable, and run it
ensure_executable "$SCRIPT"
