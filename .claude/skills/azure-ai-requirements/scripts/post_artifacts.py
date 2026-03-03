#!/usr/bin/env python3
"""
Post requirement artifact documents to Azure DevOps Discussion and update work item state to Done.

Reads three markdown files (proposal, design, tasks) and posts each as a separate
Discussion comment on the work item, followed by a summary comment.
Finally updates the work item state to Done.

Usage:
  python post_artifacts.py <work_item_id> <proposal.md> <design.md> <tasks.md> <summary>

  work_item_id  - integer ID of the work item
  proposal.md   - path to proposal document (what & why)
  design.md     - path to design document (how)
  tasks.md      - path to tasks document (implementation steps)
  summary       - brief one-line summary of what was analyzed

Environment variables:
  ADO_PAT      - Personal Access Token (required)
  ADO_ORG      - Azure DevOps organization (default: isosoman0009)
  ADO_PROJECT  - Azure DevOps project (default: ai)
  HTTP_PROXY   - HTTP/HTTPS proxy URL (optional, e.g. http://proxy:8080)
"""

import os
import sys
import json
import ssl
import base64
import re
import urllib.request
import urllib.error
from datetime import datetime

ORG = os.environ.get("ADO_ORG", "isosoman0009")
PROJECT = os.environ.get("ADO_PROJECT", "ai")
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


def markdown_to_html(text):
    """
    Convert markdown to basic HTML suitable for ADO Discussion.
    Handles headings, bold, italic, code blocks, inline code, lists, and line breaks.
    """
    lines = text.split("\n")
    html_parts = []
    in_code_block = False
    code_buffer = []

    for line in lines:
        # Code block fences
        if line.strip().startswith("```"):
            if in_code_block:
                # Close code block
                code_content = "\n".join(code_buffer)
                # Escape HTML entities inside code
                code_content = (
                    code_content.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                html_parts.append(f"<pre><code>{code_content}</code></pre>")
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Headings
        if line.startswith("### "):
            html_parts.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            html_parts.append(f"<h1>{_inline(line[2:])}</h1>")
        # List items (unordered)
        elif re.match(r"^[-*] ", line):
            html_parts.append(f"<li>{_inline(line[2:])}</li>")
        # List items with checkbox
        elif re.match(r"^- \[[ xX]\] ", line):
            checked = line[3] in "xX"
            content = line[6:]
            box = "☑" if checked else "☐"
            html_parts.append(f"<li>{box} {_inline(content)}</li>")
        # Numbered list
        elif re.match(r"^\d+\. ", line):
            content = re.sub(r"^\d+\. ", "", line)
            html_parts.append(f"<li>{_inline(content)}</li>")
        # Horizontal rule
        elif re.match(r"^---+$", line.strip()):
            html_parts.append("<hr>")
        # Empty line
        elif line.strip() == "":
            html_parts.append("<br>")
        # Regular paragraph line
        else:
            html_parts.append(f"<p>{_inline(line)}</p>")

    return "\n".join(html_parts)


def _inline(text):
    """Apply inline markdown transforms: bold, italic, inline code."""
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def read_file(path):
    """Read a markdown file, exit with error if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)


def post_discussion_comment(work_item_id, html_content, pat):
    """Post a single HTML comment to the work item Discussion."""
    url = (
        f"{BASE_URL}/{PROJECT}/_apis/wit/workItems/{work_item_id}"
        f"/comments?api-version=7.0-preview.3"
    )
    return api_request(url, pat, method="POST", data={"text": html_content})


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


def build_artifact_comment(icon, label, markdown_content):
    """Wrap a markdown document in a labeled HTML Discussion comment."""
    html_body = markdown_to_html(markdown_content)
    return (
        f"<div>"
        f"<h2>{icon} {label}</h2>"
        f"<hr>"
        f"{html_body}"
        f"</div>"
    )


def build_summary_comment(summary, timestamp):
    """Build the final summary comment HTML."""
    return (
        f"<div>"
        f"<b>🤖 AI Requirements 分析完成</b>（{timestamp}）<br><br>"
        f"<b>分析摘要：</b><br>{summary}<br><br>"
        f"<b>產出文件：</b>"
        f"<ul>"
        f"<li>📋 Proposal — 需求背景與目標</li>"
        f"<li>🏗️ Design — 技術設計方案</li>"
        f"<li>✅ Tasks — 實作工作清單</li>"
        f"</ul>"
        f"<i>由 Claude azure-ai-requirements 自動生成</i>"
        f"</div>"
    )


def main():
    if len(sys.argv) < 6:
        print(
            "Usage: python post_artifacts.py <work_item_id> <proposal.md> <design.md> <tasks.md> <summary>",
            file=sys.stderr,
        )
        sys.exit(1)

    work_item_id = int(sys.argv[1])
    proposal_path = sys.argv[2]
    design_path = sys.argv[3]
    tasks_path = sys.argv[4]
    summary = sys.argv[5]
    pat = get_pat()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read documents
    proposal_md = read_file(proposal_path)
    design_md = read_file(design_path)
    tasks_md = read_file(tasks_path)

    # Post Proposal
    print(f"Posting 📋 Proposal to work item #{work_item_id}...")
    post_discussion_comment(
        work_item_id,
        build_artifact_comment("📋", "Proposal", proposal_md),
        pat,
    )
    print("Proposal posted.")

    # Post Design
    print(f"Posting 🏗️ Design to work item #{work_item_id}...")
    post_discussion_comment(
        work_item_id,
        build_artifact_comment("🏗️", "Design", design_md),
        pat,
    )
    print("Design posted.")

    # Post Tasks
    print(f"Posting ✅ Tasks to work item #{work_item_id}...")
    post_discussion_comment(
        work_item_id,
        build_artifact_comment("✅", "Tasks", tasks_md),
        pat,
    )
    print("Tasks posted.")

    # Post summary comment
    print("Posting summary comment...")
    post_discussion_comment(
        work_item_id,
        build_summary_comment(summary, timestamp),
        pat,
    )
    print("Summary posted.")

    # Update state to Done
    print("Updating state to Done...")
    update_state_to_done(work_item_id, pat)
    print("State updated to Done.")

    print(json.dumps({
        "success": True,
        "work_item_id": work_item_id,
        "artifacts_posted": ["proposal", "design", "tasks"],
        "state": "Done",
    }))


if __name__ == "__main__":
    main()
