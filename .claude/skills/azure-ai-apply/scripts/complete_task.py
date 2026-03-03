#!/usr/bin/env python3
"""
Finalize an Azure DevOps auto-worker task after code changes are committed and a PR is created.

Steps:
  1. Add a Discussion comment summarizing what was done and linking the PR
  2. Update the work item state to Done

Usage:
  python complete_task.py <work_item_id> <pr_url> <summary_text>

  work_item_id  - integer ID of the work item
  pr_url        - URL of the created pull request
  summary_text  - brief description of what was changed (one or a few sentences)

Environment variables:
  ADO_PAT      - Personal Access Token (required)
  ADO_ORG      - Azure DevOps organization (default: isosoman0009)
  ADO_PROJECT  - Azure DevOps project (default: dev)
  HTTP_PROXY   - HTTP/HTTPS proxy URL (optional, e.g. http://proxy:8080)
"""

import os
import sys
import json
import ssl
import base64
import urllib.request
import urllib.error
from datetime import datetime

ORG = os.environ.get("ADO_ORG", "isosoman0009")
PROJECT = os.environ.get("ADO_PROJECT", "dev")
BASE_URL = f"https://dev.azure.com/{ORG}"


def _build_opener():
    """Build a urllib opener with SSL bypass and optional HTTP proxy."""
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
        print("Error: ADO_PAT environment variable not set", file=sys.stderr)
        sys.exit(1)
    return pat


def api_request(url, pat, method="GET", data=None, content_type="application/json"):
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": content_type,
        "Accept": "application/json",
    }
    req_data = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with _opener.open(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {url}: {body}")


def add_discussion_comment(work_item_id, pr_url, summary, pat):
    """Post a rich-text comment to the work item's Discussion tab."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Azure DevOps Discussion accepts HTML
    comment_html = (
        f"<div>"
        f"<b>🤖 自動任務完成</b>（{timestamp}）<br><br>"
        f"<b>執行摘要：</b><br>{summary}<br><br>"
        f"<b>Pull Request：</b><br>"
        f'<a href="{pr_url}">{pr_url}</a><br><br>'
        f"<i>由 Claude azure-auto-worker 自動執行</i>"
        f"</div>"
    )
    url = (
        f"{BASE_URL}/{PROJECT}/_apis/wit/workItems/{work_item_id}"
        f"/comments?api-version=7.0-preview.3"
    )
    return api_request(url, pat, method="POST", data={"text": comment_html})


def update_state_to_done(work_item_id, pat):
    """Patch the work item state to Done."""
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
    patch = [{"op": "replace", "path": "/fields/System.State", "value": "Done"}]
    return api_request(
        url, pat,
        method="PATCH",
        data=patch,
        content_type="application/json-patch+json",
    )


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python complete_task.py <work_item_id> <pr_url> <summary>",
            file=sys.stderr,
        )
        sys.exit(1)

    work_item_id = int(sys.argv[1])
    pr_url = sys.argv[2]
    summary = sys.argv[3]
    pat = get_pat()

    print(f"Adding Discussion comment to work item #{work_item_id}...")
    add_discussion_comment(work_item_id, pr_url, summary, pat)
    print("Comment added.")

    print("Updating state to Done...")
    update_state_to_done(work_item_id, pat)
    print("State updated to Done.")

    print(json.dumps({"success": True, "work_item_id": work_item_id, "pr_url": pr_url}))


if __name__ == "__main__":
    main()
