#!/bin/sh
# Show the newest content reads in the alfresco-access audit: who, which file, which sub-actions.
# Usage: sh audit-last.sh [count]   (needs cli.env sourced; runs as admin)
ACS_USERNAME=admin ACS_PASSWORD=admin acs audit entries list alfresco-access --include values \
  --order-by "createdAt DESC" --max-items 40 |
jq -r --argjson n "${1:-4}" '[.list.entries[].entry
  | select(.values["/alfresco-access/transaction/sub-actions"] // "" | test("Content"))
  | "\(.createdAt[11:19])  \(.values["/alfresco-access/transaction/user"])  \(.values["/alfresco-access/transaction/path"] | split("/") | last | sub("^cm:"; ""))  \(.values["/alfresco-access/transaction/sub-actions"])"]
  | .[:$n][]'
