#!/usr/bin/env python3
"""
Azure DevOps 巡邏腳本

自動查詢 isosoman0009/dev 中所有 Issue type、To Do 狀態的 work items。
對每個符合條件的 work item：
  1. 在 Discussion 留下帶時間戳的中文巡邏紀錄
  2. 將狀態更新為 Done

使用方式：
  export AZURE_DEVOPS_PAT="your_token"
  python3 patrol.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from base64 import b64encode

# ── 設定 ──────────────────────────────────────────────────────────────────
ORG = "isosoman0009"
PROJECT = "dev"
PATROL_STATE_TARGET = "Done"

# ── 認證 ──────────────────────────────────────────────────────────────────
PAT = os.environ.get("AZURE_DEVOPS_PAT", "")
if not PAT:
    print("❌ 錯誤：請先設定環境變數 AZURE_DEVOPS_PAT")
    print("   取得方式：Azure DevOps → User Settings → Personal Access Tokens")
    print("   需要權限：Work Items (Read, Write & Manage)")
    sys.exit(1)

credentials = b64encode(f":{PAT}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}
BASE_URL = f"https://dev.azure.com/{ORG}"


# ── API 函數 ───────────────────────────────────────────────────────────────

def query_work_items():
    """用 WIQL 查詢所有 Issue 類型且狀態為 To Do 的 work items"""
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/wiql?api-version=7.0"
    payload = {
        "query": (
            f"SELECT [System.Id], [System.Title], [System.State] "
            f"FROM WorkItems "
            f"WHERE [System.TeamProject] = '{PROJECT}' "
            f"AND [System.WorkItemType] = 'Issue' "
            f"AND [System.State] = 'To Do' "
            f"ORDER BY [System.Id]"
        )
    }
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("workItems", [])


def get_work_item_details(work_item_ids: list[int]) -> list[dict]:
    """批次取得 work item 詳細資訊"""
    if not work_item_ids:
        return []
    ids_str = ",".join(str(i) for i in work_item_ids)
    url = (
        f"{BASE_URL}/_apis/wit/workitems"
        f"?ids={ids_str}"
        f"&fields=System.Id,System.Title,System.State,System.WorkItemType"
        f"&api-version=7.0"
    )
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("value", [])


def add_comment(work_item_id: int, timestamp: str) -> dict:
    """在 work item 的 Discussion 新增巡邏紀錄"""
    url = (
        f"{BASE_URL}/{PROJECT}/_apis/wit/workItems/{work_item_id}/comments"
        f"?api-version=7.1-preview.3"
    )
    comment_text = (
        f"<b>🔍 自動巡邏紀錄</b><br>"
        f"巡邏時間：{timestamp}<br>"
        f"此 Issue 已完成自動巡邏確認，狀態將更新為已完成（Done）。"
    )
    resp = requests.post(url, headers=HEADERS, json={"text": comment_text}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_state(work_item_id: int, new_state: str = PATROL_STATE_TARGET) -> dict:
    """更新 work item 狀態"""
    url = f"{BASE_URL}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
    patch_headers = {**HEADERS, "Content-Type": "application/json-patch+json"}
    payload = [
        {
            "op": "add",
            "path": "/fields/System.State",
            "value": new_state,
        }
    ]
    resp = requests.patch(url, headers=patch_headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── 主程式 ────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 巡邏開始 — {timestamp}")
    print(f"📋 組織：{ORG}  |  專案：{PROJECT}")
    print("─" * 50)

    # 查詢符合條件的 work items
    print("🔍 查詢中：type=Issue、state=To Do …")
    try:
        refs = query_work_items()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        if status == 401:
            print("❌ 認證失敗（401）：PAT 可能已過期或權限不足")
        elif status == 404:
            print(f"❌ 找不到資源（404）：請確認 org={ORG}、project={PROJECT} 是否正確")
        else:
            print(f"❌ API 錯誤（{status}）：{e}")
        sys.exit(1)

    if not refs:
        print("✅ 沒有找到待巡邏的 Issues，一切正常！")
        return

    ids = [r["id"] for r in refs]
    print(f"📝 找到 {len(ids)} 個 work items：{ids}\n")

    # 取得詳細資訊
    try:
        details = get_work_item_details(ids)
    except requests.HTTPError as e:
        print(f"❌ 無法取得 work item 詳情：{e}")
        sys.exit(1)

    success_count = 0
    error_count = 0
    results = []

    for item in details:
        item_id = item["id"]
        title = item["fields"].get("System.Title", "(無標題)")
        state = item["fields"].get("System.State", "")

        print(f"  處理 #{item_id}: {title}（目前狀態：{state}）")
        try:
            add_comment(item_id, timestamp)
            print(f"    ✅ 已新增巡邏紀錄 comment")

            update_state(item_id)
            print(f"    ✅ 狀態已更新為 {PATROL_STATE_TARGET}")

            success_count += 1
            results.append({"id": item_id, "title": title, "status": "success"})
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else "?"
            msg = f"HTTP {status_code}"
            # 常見錯誤：狀態名稱不符
            if status_code == 400:
                msg += f"：狀態 '{PATROL_STATE_TARGET}' 可能不是此 project 的有效狀態，請確認工作流程設定"
            print(f"    ❌ 失敗（{msg}）")
            error_count += 1
            results.append({"id": item_id, "title": title, "status": "error", "error": msg})

    print("\n" + "=" * 50)
    print(f"🎯 巡邏完成！成功：{success_count} 個｜失敗：{error_count} 個")

    # 輸出結構化結果（供 Claude 解析）
    print("\n--- PATROL_RESULTS_JSON ---")
    print(json.dumps({
        "timestamp": timestamp,
        "total": len(ids),
        "success": success_count,
        "errors": error_count,
        "items": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
