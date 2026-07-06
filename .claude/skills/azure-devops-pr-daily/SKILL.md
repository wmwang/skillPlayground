---
name: azure-devops-pr-daily
description: |
  Azure DevOps PR 狀態即時看板與巡邏技能。當使用者提到「PR 狀態」、「PR 巡邏」、「PR dashboard」、「看看 PR」、「code review 狀況」、「審查進度」等**即時/日常** PR 狀況時，請立即使用此技能。

  自動執行以下流程：
  1. 讀取指定或預設的 Repository
  2. 查詢該 Repo 下所有處於 Active 狀態的 PR，並取得其建立時間、Reviewer 投票狀態
  3. 對每個 Active PR 查詢討論串（Threads），計算未解決（Active）的討論數
  4. 根據超時與狀態規則進行評估，產出帶有詳細資訊與風險警示的即時 PR 報告
---

# Azure DevOps PR Daily 看板技能

這個技能會掃描 Azure DevOps 中指定儲存庫（Repository）的活躍 Pull Requests，計算停留時間、未解決討論數與審查投票狀態，產出視覺化的 Dashboard 與風險分析報告。

## 前置條件

需要設定 PAT 環境變數：

```bash
export AZURE_DEVOPS_PAT="your_personal_access_token"
```

> 取得 PAT：Azure DevOps → User Settings → Personal Access Tokens
> 需要權限：Code (Read)

## 執行步驟

預設掃描特定儲存庫（可在執行時提供儲存庫名稱作為參數，或設定 `AZURE_DEVOPS_REPO` 環境變數）：

```bash
python3 .claude/skills/azure-devops-pr-daily/scripts/pr_dashboard.py [Repository名稱]
```

## 預設參數設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| Organization | `aioc` | 可透過 `AZURE_DEVOPS_ORG` 自訂 |
| Project | `messv` | 可透過 `AZURE_DEVOPS_PROJECT` 自訂 |
| 🚨 停滯 PR 閥值 | 5 天 | 停留超過此天數標記為 🔴 |
| 🟡 長期未審閥值 | 3 天 | 停留超過 3 天且無投票者標記為 🟡 |
| 📝 Draft 過久閥值 | 7 天 | Draft PR 放置超過此天數標記為 📝 |
