#!/usr/bin/env python3
"""Put the TTL #184 demo data back to its start state after a dry run. Standard library only.

  - cancel the check-out of Contracts/Service-Agreement-2027.pdf; re-create it at version 1.0 if it changed
  - move scan-*.pdf from Inbox/Claims and Inbox/Letters back to Inbox
  - delete the files created live: Invoices/*, hello-ttl184.txt in alice's home

    python3 -I reset.py --url http://localhost:8080
"""

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class Api:
    def __init__(self, url, user, password):
        self.base = url.rstrip("/") + "/alfresco/api/-default-/public/alfresco/versions/1"
        self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Authorization", self.auth)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:300]!r}")

    def node(self, parent, rel):
        r = self.call("GET", f"/nodes/{parent}?relativePath={urllib.parse.quote(rel)}&include=properties,aspectNames")
        return r["entry"] if r else None

    def children(self, node_id):
        r = self.call("GET", f"/nodes/{node_id}/children?maxItems=500&include=properties,aspectNames")
        return [e["entry"] for e in r["list"]["entries"]] if r else []


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--admin-user", default=os.environ.get("SEED_ADMIN_USER", "admin"))
    p.add_argument("--admin-password", default=os.environ.get("SEED_ADMIN_PASSWORD", "admin"))
    a = p.parse_args()
    api = Api(a.url, a.admin_user, a.admin_password)
    lib = api.call("GET", "/sites/policies/containers/documentLibrary")["entry"]["id"]

    # Check-out / check-in
    contracts = api.node(lib, "Contracts")
    for e in api.children(contracts["id"]):
        if "cm:workingcopy" in e.get("aspectNames", []):
            api.call("DELETE", f"/nodes/{e['id']}")  # deleting a working copy cancels the check-out
            print("removed working copy", e["name"])
    orig = api.node(lib, "Contracts/Service-Agreement-2027.pdf")
    if orig:
        if "cm:checkedOut" in orig.get("aspectNames", []):
            api.call("POST", f"/nodes/{orig['id']}/cancel-checkout", {})
            print("cancelled check-out")
        label = orig["properties"].get("cm:versionLabel")
        if label and label != "1.0":
            # Re-create the document so the demo starts again at version 1.0.
            api.call("DELETE", f"/nodes/{orig['id']}?permanent=true")
            seed = __import__("importlib.util").util
            spec = seed.spec_from_file_location("seed", os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed.py"))
            mod = seed.module_from_spec(spec); spec.loader.exec_module(mod)
            mod.Api(a.url, a.admin_user, a.admin_password).upload(
                contracts["id"], "Service-Agreement-2027.pdf",
                mod.pdf("Service Agreement 2027", ["Version 1", "Term: 12 months", "Fee: 10,000 EUR"]))
            print(f"re-created Service-Agreement-2027.pdf (was version {label})")

    # Drag and drop
    inbox = api.node(lib, "Inbox")
    for sub in ("Claims", "Letters"):
        f = api.node(lib, f"Inbox/{sub}")
        for e in api.children(f["id"]) if f else []:
            if e["name"].startswith("scan-"):
                api.call("POST", f"/nodes/{e['id']}/move", {"targetParentId": inbox["id"]})
                print("moved back", e["name"])
    # A drop on the site name in the breadcrumb moves the file to the site node, outside the library.
    site = api.call("GET", "/sites/policies")["entry"]["guid"]
    for e in api.children(site):
        if e["name"].startswith("scan-"):
            api.call("POST", f"/nodes/{e['id']}/move", {"targetParentId": inbox["id"]})
            print("moved back from the site node", e["name"])

    # Live-created files
    inv = api.node(lib, "Invoices")
    for e in api.children(inv["id"]) if inv else []:
        api.call("DELETE", f"/nodes/{e['id']}?permanent=true")
        print("deleted", e["name"])
    hello = api.call("GET", "/people/alice")  # exists check only
    if hello:
        home = api.node("-root-", "User Homes/alice")
        for e in api.children(home["id"]) if home else []:
            if e["name"].startswith("hello-ttl184"):
                api.call("DELETE", f"/nodes/{e['id']}?permanent=true")
                print("deleted", e["name"])
    print("reset done")


if __name__ == "__main__":
    main()
