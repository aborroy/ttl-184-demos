# TTL #184 demo scripts

Scripts and Docker Compose files used for the live demos in Tech Talk Live #184,
"Alfresco Product Demos: Straight from Engineering" (25 November 2026).

The stack runs ACS 26.3 and Alfresco Digital Workspace (ADW) 8.1 **pre-release** builds, plus
Search Enterprise. These are the versions shown in the session, not GA releases. When 26.3 is
released, use the official compose files from
[Alfresco/acs-deployment](https://github.com/Alfresco/acs-deployment) instead.

## Requirements

- Docker with at least 12 GB of memory
- A quay.io login with access to the Alfresco Enterprise images (`docker login quay.io`)
- Python 3 (the scripts use the standard library only), `curl` and `jq`
- Node.js, only for the optional browser dry run in `ui-check/`

The stack has no license file. ACS creates a 2-day trial license when the database is created.
After it expires, the repository starts in read-only mode. `make reset CONFIRM=yes && make up && make seed`
gives a new trial.

## Start

```
cd stack
make check
make up
make seed
make urls
```

ADW: `http://localhost:8080/workspace/`, user `alice`, password `alice-ttl184`.
All passwords in this repository are local demo values.

- `stack/compose.yaml`: unchanged copy of the acs-deployment pre-release compose file.
- `stack/compose.ttl184.yaml`: the changes for these demos (audit, download audit policy, cascading
  dictionaries, STOMP on ActiveMQ, Search Enterprise 5.10.0-A.6, unused services off).
- `seed.py`: user, site "Insurance Policies", folders and files for every demo, dictionaries.
- `reset.py`: puts the demo data back to its start state after a run.

## The demos

### ACS-CLI

ACS-CLI is a command line client for the Alfresco REST API, built by Jared Ottley. It is a proof of
concept in AlfrescoLabs, not an official Hyland product, and it is **not public yet**. The commands
below are what the session showed. `cli.env.example` has the environment it reads.

```
acs -o table people me
acs -o table search "TYPE:'cm:content' AND name:'signed-contract.pdf'" --max-items 4
acs -o compact events watch --type node-created
acs node create -my- --name hello-ttl184.txt --type cm:content
```

### Explicit check-out and check-in (ADW 8.1)

In ADW, Insurance Policies > Contracts: "Edit Offline" on `Service-Agreement-2027.pdf` creates a working
copy. "Upload New Version" on the working copy checks it in. Use the file
`files/Service-Agreement-2027 (Working Copy).pdf` that `seed.py` writes: in this pre-release, the
uploaded file name renames the document.

### Search within a folder (ADW 8.1)

Search for `signed-contract` (41 results), then use the "Parent folder" filter with `POL-2026-0013`
(1 result).

### Drag and drop, breadcrumb in the viewer (ADW 8.1)

Insurance Policies > Inbox: drag a `scan-*.pdf` file onto the `Claims` folder row.

### Reindex one folder (Search Enterprise 5.9.0 and later)

```
FID=$(curl -s -u alice:alice-ttl184 "http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/nodes/-root-?relativePath=Sites/policies/documentLibrary/Policies/POL-2026-0013" | jq -r .entry.id)

sh search-folder.sh $FID           # found 3
sh break-index.sh $FID             # demo only: remove the 3 files from the index
sh search-folder.sh $FID           # found 0
sh reindex-folder.sh stats $FID    # read-only report
sh reindex-folder.sh reindex $FID
sh search-folder.sh $FID           # found 3 again
```

### Audit event for content downloads (ACS 26.3)

Open `Reports/Quarterly-Report-Q3.pdf` in the viewer, then download it. The audit log shows
`readContent` for the preview and `readContent downloadContent` for the download. The property is
`audit.content.downloadPolicy=STANDARD` in `stack/compose.ttl184.yaml`. `audit-last.sh` prints the
last entries (it uses ACS-CLI; the Audit REST API gives the same data).

### Cascading dictionaries (ACS 26.2, Enterprise)

`seed.py` registers the dictionaries from `stack/cd/data/` for the model in `stack/cd/model/`.
Account number 1000 fills the account name `Cash` and the category `Current Assets`; an unknown
number (9999) is rejected with HTTP 400.

## Browser dry run (optional)

```
cd ui-check
npm install
node dryrun.cjs /tmp/ttl184-shots "../files/Service-Agreement-2027 (Working Copy).pdf"
```

It runs the ADW steps with Playwright and saves a screenshot per step.

## License

Apache License 2.0. See `LICENSE`.
