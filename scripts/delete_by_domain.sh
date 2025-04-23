#!/bin/bash

# This script deletes all documents in an Elasticsearch index that match a specific query.
# Usage: . ./delete_by_domain.sh <domain_name>
# Usage: source delete_by_domain.sh <domain_name>

# Check if the correct number of arguments is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: delete_by_domain.sh <domain_name>"
    return 1
fi

# Get the domain name from the command line and index and ES URL from environment variables
domain_name=$1
index_name=$SEARCHELASTIC_INDEX
es_hosts=$ES_HOSTS

# check if index_name and es_hosts are set
if [ -z "$index_name" ]; then
    echo "SEARCHELASTIC_INDEX is not set. Please set it to the index name."
    return 2
fi
if [ -z "$es_hosts" ]; then
    echo "ES_HOSTS is not set. Please set it to the Elasticsearch host."
    return 2
fi

# Setup values for query
es_url=`echo $ES_HOSTS | cut -f1 -d,`/$index_name
query="{ \"query\": { \"term\": { \"domain_name\": { \"value\": \"${domain_name}\" } } } }"

# Get record count before deletion
count_response=$(curl -s -k -u $ES_USER:$ES_PASSWORD -X POST "$es_url/_count" -H 'Content-Type: application/json' -d "$query")
if echo $count_response | grep -q '"count":[0-9]\+'; then
        result_count=`echo $count_response | grep -o '"count":[0-9]\+' | grep -o '[0-9]\+'`
        if [ $result_count -eq 0 ]; then
            echo "No records found for $domain_name. Exiting."
            return 0
        fi

        echo "Found $result_count records for $domain_name"
        echo "Response: $count_response"
        read -p "Are you sure you want to delete these records? " -n 1 -r

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            delete_response=$(curl -s -k -u $ES_USER:$ES_PASSWORD -X POST "$es_url/_delete_by_query" -H 'Content-Type: application/json' -d "$query")
            if echo $delete_response | grep -q '"deleted":[0-9]\+'; then
                deleted_count=$(echo "$response" | grep -o '"deleted":[0-9]\+' | grep -o '[0-9]\+')
                echo "Successfully deleted $result_count records for $domain_name"
                echo "Response: $delete_response"
            else
                echo "Failed to delete records for $domain_name."
                echo "Response: $delete_response"
            fi
        fi
else
        echo "Failed to count records for $domain_name"
        echo "Response: $count_response"
        return 3
fi
