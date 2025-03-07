#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Set a maximum wait time (seconds) to avoid infinite loops
MAX_WAIT=120

set_defaults_env() {
    export SEARCHELASTIC_INDEX="development-i14y-documents-searchgov"
    export ES_HOSTS="http://localhost:9200"
}

wait_for_elasticsearch_health() {
    local counter=0
    echo "Waiting for Elasticsearch to be healthy..."
    until curl -sS "${ES_HOSTS}/_cat/health?h=status" | grep -E -q "(green|yellow)"; do
        if (( counter >= MAX_WAIT )); then
            echo "Error: Elasticsearch did not become healthy within ${MAX_WAIT} seconds."
            return 1
        fi
        sleep 1
        ((counter++))
    done
    echo "Elasticsearch is healthy."
}

install_es_plugins() {
    local plugins=(analysis-kuromoji analysis-icu analysis-smartcn)
    for plugin in "${plugins[@]}"; do
        echo "Installing plugin: ${plugin}"
        /usr/share/elasticsearch/bin/elasticsearch-plugin install "${plugin}"
    done
}

create_es_index() {
    # Check if the index already exists
    if curl -sS --fail "${ES_HOSTS}/${SEARCHELASTIC_INDEX}" -o /dev/null 2>&1; then
        echo "Index ${SEARCHELASTIC_INDEX} already exists, skipping creation."
    else
        echo "Creating index '${SEARCHELASTIC_INDEX}'..."
        curl -X PUT "${ES_HOSTS}/${SEARCHELASTIC_INDEX}" \
             -H "Content-Type: application/json" \
             -d "@es_index_settings.json"
        echo "Index '${SEARCHELASTIC_INDEX}' created successfully."
    fi
}

restart_elasticsearch() {
    local pid
    pid=$(pgrep -f "org.elasticsearch.bootstrap.Elasticsearch" || true)
    if [ -n "$pid" ]; then
        echo "Killing Elasticsearch with PID(s): ${pid}"
        kill "$pid"
        # Allow some time for Docker to restart the process
        sleep 5
    fi
}

main() {
    set_defaults_env

    if ! wait_for_elasticsearch_health; then
        echo "Exiting due to Elasticsearch health check failure."
        exit 1
    fi

    install_es_plugins

    # Wait again after installing plugins
    if ! wait_for_elasticsearch_health; then
        echo "Exiting due to Elasticsearch health check failure after plugin installation."
        exit 1
    fi

    create_es_index
    restart_elasticsearch
}

main "$@"
