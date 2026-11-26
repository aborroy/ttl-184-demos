#!/bin/sh
# Demo only: remove the files of one folder from the Elasticsearch index, to simulate a broken index.
# The content stays in the repository; only search loses it.
# Usage: sh break-index.sh <folder-node-id>
B=http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1
for id in $(curl -s -u admin:admin "$B/nodes/$1/children?where=(isFile=true)" | jq -r '.list.entries[].entry.id'); do
  curl -s -X DELETE "http://localhost:9200/alfresco/_doc/$id?refresh=true" | jq -r '"removed from index: \(._id) \(.result)"'
done
