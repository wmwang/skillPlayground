#!/usr/bin/env python3
"""
Azure DevOps PR Dashboard 巡邏腳本

自動查詢指定 Repository 中所有 Active 狀態的 PR，
取得詳細資訊（建立時間、Reviewers、投票）並查詢未解決討論串（Active Threads），
最後輸出易讀的 ASCII 報表與結構化 JSON。

使用方式：
  export AZURE_DEVOPS_PAT="your_token"
  python3 pr_dashboard.py [Repository_Name]
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from base64 import b64encode

# ── 預設設定 ───────────────────────────────────────────────────────────────
DEFAULT_ORG = "isosoman0009"
DEFAULT_PROJECT = "dev"
DEFAULT_REPO = "my-web-app"  # 預設儲存庫

ORG = os.environ.get("AZURE_DEVOPS_ORG", DEFAULT_ORG)
PROJECT = os.environ.get("AZURE_DEVOPS_PROJECT", DEFAULT_PROJECT)

# 閥值設定
STALE_DAYS = 5
UNREVIEWED_DAYS = 3
DRAFT_STALE_DAYS = 7

# ── 認證 ──────────────────────────────────────────────────────────────────
PAT = os.environ.get("AZURE_DEVOPS_PAT", "")
if not PAT:
    # 嘗試相容 patrol 用的變數名稱
    PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT", "")

if not PAT:
    print("❌ 錯誤：請先設定環境變數 AZURE_DEVOPS_PAT 或 AZURE_DEVOPS_EXT_PAT")
    print("   取得方式：Azure DevOps → User Settings → Personal Access Tokens")
    print("   需要權限：Code (Read)")
    sys.exit(1)

credentials = b64encode(f":{PAT}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}
BASE_URL = f"https://dev.azure.com/{ORG}"


# ── API 函數 ───────────────────────────────────────────────────────────────

def get_active_pull_requests(repo_name_or_id: str) -> list[dict]:
    """取得指定 Repo 的所有 Active PR"""
    url = f"{BASE_URL}/{PROJECT}/_apis/git/repositories/{repo_name_or_id}/pullrequests?searchCriteria.status=active&api-version=7.0"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("value", [])


def get_pr_active_threads_count(repo_name_or_id: str, pr_id: int) -> int:
    """取得 PR 的討論串，並計算狀態為 active 的討論數量"""
    url = f"{BASE_URL}/{PROJECT}/_apis/git/repositories/{repo_name_or_id}/pullrequests/{pr_id}/threads?api-version=7.0"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    threads = resp.json().get("value", [])
    
    # 統計 status 為 active 且非系統自動產生的討論
    active_count = 0
    for t in threads:
        # thread status 可以是 active, resolved, closed 等
        if t.get("status") == "active":
            active_count += 1
    return active_count


# ── 輔助函數 ───────────────────────────────────────────────────────────────

def parse_iso_date(date_str: str) -> datetime:
    """解析 Azure DevOps 返回的 ISO 時間字串"""
    # 格式可能如 '2026-07-04T15:30:00Z'
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def format_row(pr_id: str, title: str, creator: str, elapsed_str: str, review_status: str, active_threads: str) -> str:
    """格式化 ASCII 表格列"""
    # 限制標題長度以防排版凌亂
    if len(title) > 28:
        title = title[:25] + "..."
    return f"│ {pr_id:<5} │ {title:<28} │ {creator:<8} │ {elapsed_str:<6} │ {review_status:<12} │ {active_threads:<10} │"


# ── 主程式 ────────────────────────────────────────────────────────────────

def main():
    # 決定 Repo
    repo = DEFAULT_REPO
    if len(sys.argv) > 1:
        repo = sys.argv[1]
    elif os.environ.get("AZURE_DEVOPS_REPO"):
        repo = os.environ["AZURE_DEVOPS_REPO"]

    now = datetime.now(timezone.utc)
    timestamp_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"📊 PR Dashboard — {timestamp_local}")
    print(f"📋 組織：{ORG} | 專案：{PROJECT} | 儲存庫：{repo}")
    print("═" * 78)

    try:
        pr_list = get_active_pull_requests(repo)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        if status == 401:
            print("❌ 認證失敗（401）：PAT 可能已過期或權限不足")
        elif status == 404:
            print(f"❌ 找不到資源（404）：請確認組織、專案或儲存庫名稱 '{repo}' 是否正確")
        else:
            print(f"❌ API 錯誤（{status}）：{e}")
        sys.exit(1)

    if not pr_list:
        print(f"✅ 目前在儲存庫 '{repo}' 中沒有任何活躍的 Pull Requests！")
        return

    # 解析 PR 詳細資訊
    processed_prs = []
    stale_count = 0
    no_reviewer_count = 0
    draft_stale_count = 0

    for pr in pr_list:
        pr_id = pr["pullRequestId"]
        title = pr["title"]
        creator = pr.get("createdBy", {}).get("displayName", "Unknown")
        is_draft = pr.get("isDraft", False)
        
        # 計算停留時間
        created_date = parse_iso_date(pr["creationDate"])
        delta = now - created_date
        days_elapsed = delta.days

        # 獲取討論數
        try:
            active_threads = get_pr_active_threads_count(repo, pr_id)
        except Exception:
            active_threads = 0

        # 解析 Reviewers 狀態
        reviewers = pr.get("reviewers", [])
        voted_reviewers = [r for r in reviewers if r.get("vote", 0) != 0]
        
        # 決定審查狀態字串
        if is_draft:
            review_status = "Draft"
        elif not reviewers:
            review_status = "無審查者"
        else:
            review_status = f"{len(voted_reviewers)}/{len(reviewers)} 已審"

        # 評估風險等級與告警標記
        risk_level = "GREEN"
        elapsed_icon = f"{days_elapsed}天"

        if is_draft:
            if days_elapsed >= DRAFT_STALE_DAYS:
                risk_level = "DRAFT_STALE"
                elapsed_icon = f"📝 {days_elapsed}天"
                draft_stale_count += 1
            else:
                elapsed_icon = f"{days_elapsed}天"
        elif not reviewers:
            risk_level = "GRAY"
            elapsed_icon = f"⚪ {days_elapsed}天"
            no_reviewer_count += 1
        elif days_elapsed >= STALE_DAYS:
            risk_level = "RED"
            elapsed_icon = f"🔴 {days_elapsed}天"
            stale_count += 1
        elif days_elapsed >= UNREVIEWED_DAYS and len(voted_reviewers) == 0:
            risk_level = "YELLOW"
            elapsed_icon = f"🟡 {days_elapsed}天"

        processed_prs.append({
            "id": pr_id,
            "title": title,
            "creator": creator,
            "days_elapsed": days_elapsed,
            "is_draft": is_draft,
            "reviewers": [{"name": r.get("displayName"), "vote": r.get("vote")} for r in reviewers],
            "active_threads_count": active_threads,
            "risk_level": risk_level,
            "elapsed_icon": elapsed_icon,
            "review_status": review_status
        })

    # 繪製表格
    print("┌" + "─"*5 + "┬" + "─"*30 + "┬" + "─"*10 + "┬" + "─"*8 + "┬" + "─"*14 + "┬" + "─"*12 + "┐")
    print(format_row(" #ID", "標題", "建立者", "停留", "審查狀態", "未解決討論"))
    print("├" + "─"*5 + "┼" + "─"*30 + "┼" + "─"*10 + "┼" + "─"*8 + "┼" + "─"*14 + "┼" + "─"*12 + "┤")
    for p in processed_prs:
        print(format_row(f"#{p['id']}", p['title'], p['creator'], p['elapsed_icon'], p['review_status'], str(p['active_threads_count'])))
    print("└" + "─"*5 + "┴" + "─"*30 + "┴" + "─"*10 + "┴" + "─"*8 + "┴" + "─"*14 + "┴" + "─"*12 + "┘")

    # 印出警示
    print("\n🚨 風險告警：")
    warnings_found = False
    for p in processed_prs:
        if p["risk_level"] == "RED":
            print(f"  🔴 PR #{p['id']} ({repo}) 已停留 {p['days_elapsed']} 天、有 {p['active_threads_count']} 個未解決討論 → 建議催促審查者")
            warnings_found = True
        elif p["risk_level"] == "YELLOW":
            print(f"  🟡 PR #{p['id']} ({repo}) 已停留 {p['days_elapsed']} 天且無人投票 → 建議催促進行 Code Review")
            warnings_found = True
        elif p["risk_level"] == "GRAY":
            print(f"  ⚪ PR #{p['id']} ({repo}) 尚未指定任何 Reviewer → 建議盡快指派")
            warnings_found = True
        elif p["risk_level"] == "DRAFT_STALE":
            print(f"  📝 PR #{p['id']} ({repo}) 為 Draft 且已放置 {p['days_elapsed']} 天 → 建議確認開發狀況")
            warnings_found = True
            
    if not warnings_found:
        print("  ✅ 目前沒有高風險 PR，表現優異！")

    # 管理建議
    print("\n💡 管理建議：")
    if stale_count > 0:
        print(f"  • 目前有 {stale_count} 個 PR 嚴重停滯（超過 {STALE_DAYS} 天），可能遇到了障礙，建議安排集中審查。")
    if no_reviewer_count > 0:
        print(f"  • 有 {no_reviewer_count} 個 PR 缺少審查者，可能會被遺漏。")
    if draft_stale_count > 0:
        print(f"  • 有 {draft_stale_count} 個 Draft PR 放置過久，建議確認是否需要調整或關閉。")
    if not (stale_count or no_reviewer_count or draft_stale_count):
        print("  • 所有 Active PR 都在正常處理週期內，請繼續保持！")


if __name__ == "__main__":
    main()
