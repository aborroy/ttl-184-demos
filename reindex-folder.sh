#!/bin/sh
# Run the Search Enterprise reindexing app on one folder subtree (released in Search Enterprise 5.9.0).
#   sh reindex-folder.sh stats   <folder-node-id>   read-only report: node count, types, id range
#   sh reindex-folder.sh reindex <folder-node-id>   reindex the folder and every node below it
# Prints the interesting log lines only. Run from anywhere.
cd "$(dirname "$0")/stack" || exit 1
case "$1" in
  stats) JOB=showFolderChildRange ;;
  reindex) JOB=reindexByFolderNode ;;
  *) echo "usage: sh reindex-folder.sh stats|reindex <folder-node-id>"; exit 1 ;;
esac
docker compose -p ttl184-demo -f compose.yaml -f compose.ttl184.yaml run --rm --no-deps \
  -e ALFRESCO_REINDEX_JOBNAME=$JOB -e ALFRESCO_REINDEX_FOLDERNODEID="$2" search-reindexing 2>&1 |
  awk '/Folder Subtree Report/{r=1} r&&/Example usage/{r=0} r{print; next}
       /finished with status/{sub(/.*: /,""); print "reindex: " $0; fflush()}'
