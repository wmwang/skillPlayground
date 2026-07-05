#!/usr/bin/env python3
"""
Azure DevOps PR Monthly Metrics 統計腳本

自動查詢指定 Repository 在過去 30 天內所有 Completed（已合併）的 PR，
統計並計算：
  1. PR 總量與趨勢
  2. 平均與中位數合併時間 (Lead Time)
  3. 審查品質指標（平均 Reviewers 數量、平均討論 thread 數量）
  4. 貢獻者與審查者活躍度排行

使用方式：
  export AZURE_DEVOPS_PAT="your_token"
  python3 pr_metrics.py [Repository_Name] [天數, 預設 30]
"""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from base64 import b64encode
import statistics

# ── 預設設定 ───────────────────────────────────────────────────────────────
DEFAULT_ORG = "isosoman0009"
DEFAULT_PROJECT = "dev"
DEFAULT_REPO = "my-web-app"

ORG = os.environ.get("AZURE_DEVOPS_ORG", DEFAULT_ORG)
PROJECT = os.environ.get("AZURE_DEVOPS_PROJECT", DEFAULT_PROJECT)

# ── 認證 ──────────────────────────────────────────────────────────────────
PAT = os.environ.get("AZURE_DEVOPS_PAT", "") or os.environ.get("AZURE_DEVOPS_EXT_PAT", "")
if not PAT:
    print("❌ 錯誤：請先設定環境變數 AZURE_DEVOPS_PAT 或 AZURE_DEVOPS_EXT_PAT")
    sys.exit(1)

credentials = b64encode(f":{PAT}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}
BASE_URL = f"https://dev.azure.com/{ORG}"


# ── API 函數 ───────────────────────────────────────────────────────────────

def get_completed_pull_requests(repo_name_or_id: str, days: int) -> list[dict]:
    """取得過去 N 天內狀態為 completed 的 PR"""
    # 由於 REST API 篩選條件限制，我們抓取 completed 狀態的 PR，並在本地篩選時間
    url = f"{BASE_URL}/{PROJECT}/_apis/git/repositories/{repo_name_or_id}/pullrequests?searchCriteria.status=completed&$top=100&api-version=7.0"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    all_prs = resp.json().get("value", [])
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    filtered_prs = []
    for pr in all_prs:
        closed_date_str = pr.get("closedDate")
        if closed_date_str:
            closed_date = datetime.fromisoformat(closed_date_str.replace("Z", "+00:00"))
            if closed_date >= cutoff_date:
                filtered_prs.append(pr)
                
    return filtered_prs


def get_pr_threads(repo_name_or_id: str, pr_id: int) -> list[dict]:
    """取得 PR 的所有討論串"""
    url = f"{BASE_URL}/{PROJECT}/_apis/git/repositories/{repo_name_or_id}/pullrequests/{pr_id}/threads?api-version=7.0"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("value", [])
    except Exception:
        return []


# ── 主程式 ────────────────────────────────────────────────────────────────

def main():
    repo = DEFAULT_REPO
    days = 30

    if len(sys.argv) > 1:
        repo = sys.argv[1]
    elif os.environ.get("AZURE_DEVOPS_REPO"):
        repo = os.environ["AZURE_DEVOPS_REPO"]

    if len(sys.argv) > 2:
        try:
            days = int(sys.argv[2])
        except ValueError:
            pass

    print(f"📊 PR 歷史表現月度度量統計報告 (過去 {days} 天)")
    print(f"📋 組織：{ORG} | 專案：{PROJECT} | 儲存庫：{repo}")
    print("═" * 78)

    try:
        completed_prs = get_completed_pull_requests(repo, days)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        if status == 404:
            print(f"❌ 找不到儲存庫 '{repo}'。請確認名稱是否正確。")
        else:
            print(f"❌ API 錯誤（{status}）：{e}")
        sys.exit(1)

    if not completed_prs:
        print(f"⚪ 過去 {days} 天內在儲存庫 '{repo}' 中無任何已合併 (Completed) 的 Pull Requests。")
        return

    total_prs = len(completed_prs)
    lead_times_hours = []
    total_comments_count = 0
    total_reviewers_count = 0

    creator_counts = {}
    reviewer_counts = {}

    print(f"🔍 正在深入分析 {total_prs} 個已合併的 PR ...")

    for pr in completed_prs:
        pr_id = pr["pullRequestId"]
        creator = pr.get("createdBy", {}).get("displayName", "Unknown")
        creator_counts[creator] = creator_counts.get(creator, 0) + 1

        # 計算合併時間 (Lead Time)
        created_date = datetime.fromisoformat(pr["creationDate"].replace("Z", "+00:00"))
        closed_date = datetime.fromisoformat(pr["closedDate"].replace("Z", "+00:00"))
        duration = closed_date - created_date
        duration_hours = duration.total_seconds() / 3600.0
        lead_times_hours.append(duration_hours)

        # 統計 Reviewers
        reviewers = pr.get("reviewers", [])
        total_reviewers_count += len(reviewers)
        for r in reviewers:
            r_name = r.get("displayName")
            if r.get("vote", 0) != 0:  # 有進行審查投票才計入
                reviewer_counts[r_name] = reviewer_counts.get(r_name, 0) + 1

        # 統計討論串數量
        threads = get_pr_threads(repo, pr_id)
        # 過濾非系統自動產生的真實討論
        user_threads = [t for t in threads if t.get("comments") and not any("system" in str(c.get("author", {}).get("uniqueName", "")).lower() for c in t.get("comments", []))]
        total_comments_count += len(user_threads)

    # 計算統計數值
    avg_lead_time_hours = sum(lead_times_hours) / total_prs
    median_lead_time_hours = statistics.median(lead_times_hours)
    
    avg_reviewers = total_reviewers_count / total_prs
    avg_comments = total_comments_count / total_prs

    # 輸出統計摘要
    print("\n📈 統計摘要與指標：")
    print(f"  • 已合併 PR 總數：{total_prs} 個")
    print(f"  • 平均合併時間 (Average Lead Time)：{avg_lead_time_hours:.1f} 小時 ({avg_lead_time_hours/24:.1f} 天)")
    print(f"  • 中位數合併時間 (Median Lead Time)：{median_lead_time_hours:.1f} 小時 ({median_lead_time_hours/24:.1f} 天)")
    print(f"  • 平均每個 PR 討論次數：{avg_comments:.1f} 次")
    print(f"  • 平均每個 PR 審查者人數：{avg_reviewers:.1f} 人")

    # 效能評語 (KPI 評估)
    print("\n💡 效能簡評：")
    if median_lead_time_hours < 24:
        print("  🟢 合併效率卓越：過半數的 PR 能在 24 小時內完成 Review 與合併。")
    elif median_lead_time_hours < 72:
        print("  🟡 合併效率正常：PR 處理時間尚可，但仍有優化空間。")
    else:
        print("  🔴 合併效率偏低：過半數的 PR 合併時間超過 3 天，可能存在 Reviewer 不足或 PR 規模過大的問題。")

    if avg_comments < 1.0:
        print("  ⚠️ 審查深度不足：平均每個 PR 討論次數少於 1 次，建議提高代碼審查的互動與品質把關。")
    elif avg_comments >= 3.0:
        print("  🟢 審查深度良好：討論互動熱烈，代碼把關嚴謹。")

    # 輸出排行榜
    print("\n🏆 團隊活躍度排行 (Top 3)：")
    
    # 貢獻者排行
    sorted_creators = sorted(creator_counts.items(), key=lambda x: x[1], reverse=True)
    print("  【PR 貢獻者】")
    for i, (name, count) in enumerate(sorted_creators[:3], start=1):
        print(f"    {i}. {name} ({count} 個 PR)")

    # 審查者排行
    sorted_reviewers = sorted(reviewer_counts.items(), key=lambda x: x[1], reverse=True)
    print("  【活躍審查者】")
    for i, (name, count) in enumerate(sorted_reviewers[:3], start=1):
        print(f"    {i}. {name} ({count} 次有效投票)")


if __name__ == "__main__":
    main()
