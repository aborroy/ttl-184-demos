#!/bin/sh
# Count what search finds inside one folder (ANCESTOR query), as alice.
# Usage: sh search-folder.sh <folder-node-id>
B=http://localhost:8080/alfresco/api/-default-/public/search/versions/1
cat > /tmp/ttl184-q.json <<JSON
{"query": {"language": "afts", "query": "ANCESTOR:\"workspace://SpacesStore/$1\" AND TYPE:\"cm:content\""}}
JSON
curl -s -u alice:alice-ttl184 -X POST "$B/search" -H 'Content-Type: application/json' -d @/tmp/ttl184-q.json |
  jq -r 'if .error then "error: \(.error.briefSummary)" else "found \(.list.pagination.totalItems): \([.list.entries[].entry.name] | join(", "))" end'
