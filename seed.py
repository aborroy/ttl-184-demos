#!/usr/bin/env python3
"""Seed the TTL #184 demo stack. Standard library only. Safe to run twice (existing items are kept).

What it creates, and which demo uses it:

  user alice (Alice Martin)                      the presenter logs in as alice in ADW
  site "policies" (Insurance Policies)
    Policies/POL-2026-0001 .. 0040/              search within a folder: every folder holds the
      signed-contract.pdf, identity-card.pdf,    same three file names
      claim-form.pdf
    Contracts/Service-Agreement-2027.pdf         check-out / check-in (new version in files/)
    Inbox/ (5 files, Claims/, Letters/)          drag and drop onto a folder or the breadcrumb
    Archive/2026/
    Reports/Quarterly-Report-Q3.pdf              download audit event
    Reports/Large-Claims-Register.xlsx           a large Excel file (also kept in files/)
    Invoices/                                    cascading dictionaries: classify here live
  cascading dictionaries cdict:department, cdict:account (data from stack/cd/data/)

Local files for the live part are written to files/.

    python3 -I seed.py --url http://localhost:8080
"""

import argparse
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE / "files"
CD_DATA = HERE / "stack" / "cd" / "data"

SITE = "policies"
USER = "alice"
POLICY_FOLDERS = 40
POLICY_FILES = ["signed-contract.pdf", "identity-card.pdf", "claim-form.pdf"]


class Api:
    def __init__(self, url, user, password):
        self.base = url.rstrip("/") + "/alfresco/api/-default-/public/alfresco/versions/1"
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"

    def call(self, method, path, body=None, ctype="application/json", ok_conflict=True):
        data = body
        if body is not None and ctype == "application/json":
            data = json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Authorization", self.auth)
        if data is not None:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 409 and ok_conflict:
                return None
            raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:400]!r}")

    def upload(self, parent_id, name, content, relative_path=None):
        boundary = uuid.uuid4().hex
        parts = []
        fields = {"name": name}
        if relative_path:
            fields["relativePath"] = relative_path
        for k, v in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="filedata"; filename="{name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n".encode()
            + content
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        return self.call("POST", f"/nodes/{parent_id}/children", b"".join(parts),
                         ctype=f"multipart/form-data; boundary={boundary}")


def pdf(title, lines):
    """A one-page PDF with a title and some lines of text."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    text = ["BT /F1 20 Tf 60 760 Td (" + esc(title) + ") Tj ET"]
    y = 720
    for line in lines:
        text.append(f"BT /F1 12 Tf 60 {y} Td (" + esc(line) + ") Tj ET")
        y -= 20
    stream = "\n".join(text).encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def xlsx(sheets, rows, cols=10):
    """A large .xlsx (inline strings and numbers), built without third-party libraries."""
    def col(i):
        s = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s
    regions = ["North", "South", "East", "West", "Central"]
    kinds = ["Motor", "Home", "Travel", "Health", "Liability"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(1, sheets + 1))
                   + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="Claims {2020 + i}" sheetId="{i}" r:id="rId{i}"/>' for i in range(1, sheets + 1))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                             for i in range(1, sheets + 1))
                   + "</Relationships>")
        header = ["Claim", "Policy", "Region", "Kind", "Opened", "Amount", "Reserve", "Paid", "Status", "Handler"]
        for s in range(1, sheets + 1):
            with z.open(f"xl/worksheets/sheet{s}.xml", "w") as f:
                f.write(b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
                cells = "".join(f'<c r="{col(c)}1" t="inlineStr"><is><t>{header[c]}</t></is></c>' for c in range(cols))
                f.write(f'<row r="1">{cells}</row>'.encode())
                for r in range(2, rows + 2):
                    n = s * 1_000_000 + r
                    vals = [
                        ("s", f"CLM-{2020 + s}-{r:06d}"), ("s", f"POL-2026-{n % 4000 + 1:04d}"),
                        ("s", regions[n % 5]), ("s", kinds[(n // 5) % 5]), ("s", f"{2020 + s}-{n % 12 + 1:02d}-{n % 28 + 1:02d}"),
                        ("n", (n * 37) % 50000 + 100), ("n", (n * 13) % 20000), ("n", (n * 7) % 30000),
                        ("s", "Open" if n % 3 else "Closed"), ("s", f"Handler {n % 40 + 1}"),
                    ]
                    cells = "".join(
                        f'<c r="{col(c)}{r}" t="inlineStr"><is><t>{v}</t></is></c>' if t == "s" else f'<c r="{col(c)}{r}"><v>{v}</v></c>'
                        for c, (t, v) in enumerate(vals[:cols]))
                    f.write(f'<row r="{r}">{cells}</row>'.encode())
                f.write(b"</sheetData></worksheet>")
    return buf.getvalue()


def node_id(api, parent, relative_path):
    try:
        req = urllib.request.Request(api.base + f"/nodes/{parent}?relativePath={urllib.request.quote(relative_path)}")
        req.add_header("Authorization", api.auth)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["entry"]["id"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def folder(api, parent, relative_path):
    existing = node_id(api, parent, relative_path)
    if existing:
        return existing
    *head, name = relative_path.split("/")
    body = {"name": name, "nodeType": "cm:folder"}
    if head:
        body["relativePath"] = "/".join(head)
    return api.call("POST", f"/nodes/{parent}/children", body)["entry"]["id"]


def put_file(api, parent, relative_dir, name, content):
    if node_id(api, parent, f"{relative_dir}/{name}"):
        return False
    api.upload(parent, name, content, relative_dir)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--admin-user", default=os.environ.get("SEED_ADMIN_USER", "admin"))
    p.add_argument("--admin-password", default=os.environ.get("SEED_ADMIN_PASSWORD", "admin"))
    p.add_argument("--user-password", default=os.environ.get("DEMO_USER_PASSWORD", "alice-ttl184"))
    p.add_argument("--excel-rows", type=int, default=60000, help="rows per sheet")
    p.add_argument("--excel-sheets", type=int, default=5)
    a = p.parse_args()

    api = Api(a.url, a.admin_user, a.admin_password)
    FILES.mkdir(exist_ok=True)

    # User and site
    if api.call("POST", "/people", {"id": USER, "firstName": "Alice", "lastName": "Martin",
                                    "email": "alice@example.com", "password": a.user_password}) is not None:
        print("created user alice")
    if api.call("POST", "/sites", {"id": SITE, "title": "Insurance Policies",
                                   "description": "TTL #184 demo site", "visibility": "PRIVATE"}) is not None:
        print("created site policies")
    api.call("POST", f"/sites/{SITE}/members", {"role": "SiteManager", "id": USER})
    lib = api.call("GET", f"/sites/{SITE}/containers/documentLibrary")["entry"]["id"]

    # Search within a folder
    made = 0
    for i in range(1, POLICY_FOLDERS + 1):
        pol = f"POL-2026-{i:04d}"
        folder(api, lib, f"Policies/{pol}")
        for name in POLICY_FILES:
            title = name.replace("-", " ").replace(".pdf", "").title()
            made += put_file(api, lib, f"Policies/{pol}", name,
                             pdf(f"{title} - {pol}", [f"Policy number: {pol}", f"Holder: Customer {i:03d}",
                                                     "Document type: " + title, "TTL #184 demo document"]))
    print(f"policy files uploaded: {made}")

    # Check-out / check-in
    put_file(api, lib, "Contracts", "Service-Agreement-2027.pdf",
             pdf("Service Agreement 2027", ["Version 1", "Term: 12 months", "Fee: 10,000 EUR"]))
    # ADW names the checked-in document after the uploaded file. A file named like the original fails
    # ("same name already exists"); a file named like the working copy keeps the original name.
    (FILES / "Service-Agreement-2027 (Working Copy).pdf").write_bytes(
        pdf("Service Agreement 2027", ["Version 2 (checked in live)", "Term: 24 months", "Fee: 18,000 EUR"]))

    # Drag and drop, breadcrumb
    folder(api, lib, "Archive/2026")
    folder(api, lib, "Inbox/Claims")
    folder(api, lib, "Inbox/Letters")
    for n in range(1, 6):
        put_file(api, lib, "Inbox", f"scan-{n:03d}.pdf", pdf(f"Scanned letter {n:03d}", ["Received by post", "To be filed"]))

    # Download audit
    put_file(api, lib, "Reports", "Quarterly-Report-Q3.pdf",
             pdf("Quarterly Report Q3 2026", ["Claims opened: 1,204", "Claims closed: 1,150"]))

    # Excel partial preview
    xl = FILES / "Large-Claims-Register.xlsx"
    if not xl.exists():
        xl.write_bytes(xlsx(a.excel_sheets, a.excel_rows))
    print(f"excel file: {xl.stat().st_size / 1_048_576:.1f} MiB")
    put_file(api, lib, "Reports", xl.name, xl.read_bytes())

    # Cascading dictionaries
    folder(api, lib, "Invoices")
    dicts = [
        ("cdict:department", "Departments", "cdict:departmentId", "cdict:departmentDictVersion", "departments.json"),
        ("cdict:account", "Chart of Accounts", "cdict:accountNumber", "cdict:accountDictVersion", "accounts.json"),
    ]
    for aspect, name, key, version, data in dicts:
        created = api.call("POST", "/cascading-dictionaries",
                           {"name": name, "aspect": aspect, "keyProperty": key, "versionProperty": version})
        if created is not None:
            api.call("POST", f"/cascading-dictionaries/{aspect}/content?majorVersion=true",
                     json.loads((CD_DATA / data).read_text()))
            print(f"created dictionary {aspect}")

    print("seed done. ADW: " + a.url.rstrip("/") + "/workspace/  user: alice")


if __name__ == "__main__":
    sys.exit(main())
