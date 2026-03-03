#!/usr/bin/env python3
"""
Fetch SDD (Software Design Documents) for an Azure DevOps Development work item.

Strategy:
  1. Check if the Development work item itself has SDD comments (direct posting case)
  2. If not, traverse to the parent work item and find the sibling with
     activity=Requirements and [AI] in the title — that's where azure-ai-requirements
     posted the SDD artifacts.

This prevents cross-contamination when multiple [AI] work items exist in the project.

Usage:
  python fetch_sdd.py <development_work_item_id>

Outputs JSON:
  {"found": true,  "source_id": 55, "proposal": "...", "design": "...", "tasks": "..."}
  {"found": false, "reason": "..."}

Environment variables:
  ADO_PAT      - Personal Access Token (required)
  ADO_ORG      - Azure DevOps organization (default: isosoman0009)
  ADO_PROJECT  - Azure DevOps project (default: ai)
  HTTP_PROXY   - HTTP/HTTPS proxy URL (optional)
"""

import os
import sys
import json
import ssl
import base64
import re
import urllib.request
import urllib.error

ORG = os.environ.get("ADO_ORG", "isosoman0009")
PROJECT = os.environ.get("ADO_PROJECT", "ai")
BASE_URL = f"https://dev.azure.com/{ORG}"


def _build_opener():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    handlers = [urllib.request.HTTPSHandler(context=ssl_ctx)]
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if proxy:
        handlers.insert(0, urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


_opener = _build_opener()


def get_pat():
    pat = os.environ.get("ADO_PAT", "")
    if not pat:
        print(json.dumps({"found": False, "reason": "ADO_PAT environment variable not set"}))
        sys.exit(1)
    return pat


def api_get(url, pat):
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    })
    try:
        with _opener.open(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {url}: {body}")


def get_work_item(wid, pat):
    """Fetch a work item with all relations expanded."""
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/workitems/{wid}?$expand=relations&api-version=7.0"
    return api_get(url, pat)


def get_comments(wid, pat):
    """Fetch all Discussion comments for a work item."""
    url = (
        f"{BASE_URL}/{PROJECT}/_apis/wit/workItems/{wid}"
        f"/comments?api-version=7.0-preview.3"
    )
    data = api_get(url, pat)
    return data.get("comments", [])


def extract_wid_from_url(url):
    """Parse a work item ID from an ADO REST URL like .../workItems/42."""
    m = re.search(r"/workItems/(\d+)$", url, re.IGNORECASE)
    return int(m.group(1)) if m else None


def get_parent_id(work_item):
    """
    Return the parent work item ID by looking for a Hierarchy-Reverse relation.
    This is the standard ADO parent link.
    """
    for rel in work_item.get("relations") or []:
        if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
            wid = extract_wid_from_url(rel.get("url", ""))
            if wid:
                return wid
    return None


def get_child_ids(work_item):
    """Return all direct child work item IDs via Hierarchy-Forward relations."""
    children = []
    for rel in work_item.get("relations") or []:
        if rel.get("rel") == "System.LinkTypes.Hierarchy-Forward":
            wid = extract_wid_from_url(rel.get("url", ""))
            if wid:
                children.append(wid)
    return children


def find_requirements_siblings(dev_work_item, pat):
    """
    Find sibling work items that have:
    - activity = Requirements
    - [AI] in the title

    Traversal: dev work item → parent → children (siblings) → filter by Requirements + [AI].
    Returns a list of matching work item IDs.
    """
    parent_id = get_parent_id(dev_work_item)
    if not parent_id:
        return []

    parent = get_work_item(parent_id, pat)
    sibling_ids = get_child_ids(parent)

    dev_id = dev_work_item["id"]
    results = []
    for sid in sibling_ids:
        if sid == dev_id:
            continue  # skip self
        try:
            sibling = get_work_item(sid, pat)
            fields = sibling.get("fields", {})
            activity = fields.get("Microsoft.VSTS.Common.Activity", "")
            title = fields.get("System.Title", "")
            if activity == "Requirements" and "[AI]" in title.upper():
                results.append(sid)
        except RuntimeError:
            continue  # skip inaccessible items

    return results


# ── SDD comment detection ────────────────────────────────────────────────────

def classify_comment(text):
    """
    Identify which SDD artifact a Discussion comment contains.
    azure-ai-requirements posts with <h2>ICON LABEL</h2> headers.
    Returns 'proposal', 'design', 'tasks', or None.
    """
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", text, re.IGNORECASE | re.DOTALL)
    if not h2:
        return None
    header = h2.group(1).lower()
    if "proposal" in header:
        return "proposal"
    if "design" in header:
        return "design"
    if "tasks" in header:
        return "tasks"
    return None


def extract_body(html):
    """
    Strip the post_artifacts.py wrapper (<div><h2>...</h2><hr>...</div>)
    and convert the inner HTML to readable markdown-ish plain text.
    """
    text = re.sub(r"^<div>", "", html.strip())
    text = re.sub(r"</div>$", "", text.strip())
    # Remove header block
    text = re.sub(r"<h2[^>]*>.*?</h2>\s*<hr>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Convert headings
    text = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda m: "#" * int(m.group(1)) + " " + m.group(2) + "\n",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li>(.*?)</li>", r"- \1", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(
        r"<pre><code>(.*?)</code></pre>",
        lambda m: "```\n" + m.group(1) + "\n```",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_sdd_from_comments(comments):
    """
    Scan a list of Discussion comments and extract SDD artifacts.
    Returns a dict with keys 'proposal', 'design', 'tasks' (those found), or {}.
    """
    sdd = {}
    for comment in comments:
        artifact = classify_comment(comment.get("text", ""))
        if artifact and artifact not in sdd:
            sdd[artifact] = extract_body(comment["text"])
    return sdd


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_sdd.py <development_work_item_id>", file=sys.stderr)
        sys.exit(1)

    dev_id = int(sys.argv[1])
    pat = get_pat()

    dev_item = get_work_item(dev_id, pat)

    # ── Step 1: Check the Development work item's own Discussion first ──
    # (handles the case where SDD was posted directly on this work item)
    comments = get_comments(dev_id, pat)
    sdd = extract_sdd_from_comments(comments)

    if sdd.get("tasks"):
        print(json.dumps({
            "found": True,
            "source_id": dev_id,
            "source": "self",
            "proposal": sdd.get("proposal", ""),
            "design": sdd.get("design", ""),
            "tasks": sdd["tasks"],
        }, ensure_ascii=False, indent=2))
        return

    # ── Step 2: Traverse to parent → find Requirements siblings ──
    req_sibling_ids = find_requirements_siblings(dev_item, pat)

    if not req_sibling_ids:
        parent_id = get_parent_id(dev_item)
        reason = (
            "No parent work item found — cannot locate Requirements sibling"
            if not parent_id
            else f"Parent #{parent_id} has no [AI] Requirements siblings"
        )
        print(json.dumps({"found": False, "reason": reason}))
        return

    # Check each Requirements sibling's Discussion (use the most recent one found)
    for sid in req_sibling_ids:
        sib_comments = get_comments(sid, pat)
        sdd = extract_sdd_from_comments(sib_comments)
        if sdd.get("tasks"):
            print(json.dumps({
                "found": True,
                "source_id": sid,
                "source": "requirements_sibling",
                "proposal": sdd.get("proposal", ""),
                "design": sdd.get("design", ""),
                "tasks": sdd["tasks"],
            }, ensure_ascii=False, indent=2))
            return

    print(json.dumps({
        "found": False,
        "reason": (
            f"Found Requirements sibling(s) {req_sibling_ids} "
            f"but none have SDD comments (Proposal/Design/Tasks) in Discussion"
        ),
    }))


if __name__ == "__main__":
    main()
