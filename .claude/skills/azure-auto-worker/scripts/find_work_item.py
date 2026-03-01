#!/usr/bin/env python3
"""
Find the latest Azure DevOps work item with:
  - Title containing '[auto]'
  - State = 'To Do'
  - Development has a Branch linked

Outputs JSON to stdout with work item details and branch/repo info.
On failure or not found, outputs JSON with {"found": false, "reason": "..."}.
"""

import os
import sys
import json
import base64
import re
import urllib.parse
import urllib.request
import urllib.error

ORG = "isosoman0009"
PROJECT = "dev"
BASE_URL = f"https://dev.azure.com/{ORG}"


def get_pat():
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT", "")
    if not pat:
        out = {"found": False, "reason": "AZURE_DEVOPS_EXT_PAT environment variable not set"}
        print(json.dumps(out))
        sys.exit(1)
    return pat


def make_request(url, pat, method="GET", data=None, content_type="application/json"):
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": content_type,
        "Accept": "application/json",
    }
    req_data = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {url}: {body}")


def find_candidate_ids(pat):
    """WIQL query: [auto] in title, To Do, newest first."""
    wiql = {
        "query": (
            "SELECT [System.Id] FROM WorkItems "
            "WHERE [System.TeamProject] = 'dev' "
            "AND [System.Title] CONTAINS '[auto]' "
            "AND [System.State] = 'To Do' "
            "ORDER BY [System.CreatedDate] DESC"
        )
    }
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/wiql?api-version=7.0"
    result = make_request(url, pat, method="POST", data=wiql)
    return [item["id"] for item in result.get("workItems", [])]


def get_work_item(wid, pat):
    """Fetch work item with full relations expanded."""
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/workitems/{wid}?$expand=relations&api-version=7.0"
    return make_request(url, pat)


def parse_branch_relation(relation):
    """
    Extract repo_id and branch name from an ArtifactLink Branch relation URL.

    URL format: vstfs:///Git/Ref/{projectId}%2F{repoId}%2FGB{urlEncodedBranchName}
    The 'GB' prefix means 'Git Branch'. Branch name slashes are encoded as %2F.
    """
    url = relation.get("url", "")
    if not url.startswith("vstfs:///Git/Ref/"):
        return None

    path = url[len("vstfs:///Git/Ref/"):]
    # Split into exactly 3 parts: projectId, repoId, GB+branchName
    parts = path.split("%2F", 2)
    if len(parts) < 3:
        return None

    repo_id = urllib.parse.unquote(parts[1])
    branch_raw = parts[2]  # e.g. "GBfeature%2Fmy-task"
    if not branch_raw.startswith("GB"):
        return None
    branch = urllib.parse.unquote(branch_raw[2:])  # strip "GB" prefix
    return {"repo_id": repo_id, "branch": branch}


def get_repo_info(repo_id, pat):
    """Fetch repository details by ID."""
    url = f"{BASE_URL}/{PROJECT}/_apis/git/repositories/{repo_id}?api-version=7.0"
    return make_request(url, pat)


def strip_html(text):
    """Convert Azure DevOps rich-text HTML description to plain text."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def main():
    pat = get_pat()

    candidate_ids = find_candidate_ids(pat)
    if not candidate_ids:
        print(json.dumps({"found": False, "reason": "No [auto] work items with state 'To Do' found"}))
        return

    for wid in candidate_ids:
        item = get_work_item(wid, pat)
        relations = item.get("relations") or []

        for rel in relations:
            if rel.get("attributes", {}).get("name") != "Branch":
                continue

            branch_info = parse_branch_relation(rel)
            if not branch_info:
                continue

            # Found a valid branch — fetch repo details
            repo = get_repo_info(branch_info["repo_id"], pat)
            clone_url = repo.get("remoteUrl", "")
            repo_name = repo.get("name", "")
            # Default branch e.g. "refs/heads/main" -> "main"
            default_branch = repo.get("defaultBranch", "refs/heads/main").replace("refs/heads/", "")

            fields = item.get("fields", {})
            result = {
                "found": True,
                "work_item_id": wid,
                "title": fields.get("System.Title", ""),
                "description": strip_html(fields.get("System.Description", "")),
                "branch": branch_info["branch"],
                "repo_id": branch_info["repo_id"],
                "repo_name": repo_name,
                "clone_url": clone_url,
                "default_branch": default_branch,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    print(json.dumps({
        "found": False,
        "reason": "Found [auto] To Do work items, but none have a Development Branch linked"
    }))


if __name__ == "__main__":
    main()
