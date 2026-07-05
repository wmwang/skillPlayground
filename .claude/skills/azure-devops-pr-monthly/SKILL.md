---
name: azure-devops-pr-monthly
description: |
  Azure DevOps PR 歷史表現度量統計技能。當使用者提到「PR 統計」、「PR 歷史績效」、「PR 月度度量」、「績效回顧」、「代碼審查統計」、「PR metrics」等**回顧/統計** PR 表現時，請立即使用此技能。

  自動執行以下流程：
  1. 讀取指定或預設的 Repository 以及回顧天數
  2. 查詢該 Repo 下過去指定天數（預設 30 天）內所有處於 Completed（已合併）狀態的 PR
  3. 計算平均與中位數合併時間 (Lead Time)
  4. 統計代碼審查討論互動次數（排除系統自動產生的訊息）與 Reviewer 參與度
  5. 產出團隊活躍度排行（貢獻者與審查者）與簡評
---

# Azure DevOps PR Monthly 績效統計技能

這個技能會統計過去一段時間（預設 30 天）內已合併的 Pull Requests，分析團隊的代碼審查時效、討論深度與活躍成員排行，產出歷史度量報告。

## 前置條件

需要設定 PAT 環境變數：

```bash
export AZURE_DEVOPS_PAT="your_personal_access_token"
```

> 取得 PAT：Azure DevOps → User Settings → Personal Access Tokens
> 需要權限：Code (Read)

## 執行步驟

預設掃描特定儲存庫過去 30 天的資料（可在執行時提供儲存庫名稱與天數作為參數，或設定 `AZURE_DEVOPS_REPO` 環境變數）：

```bash
python3 .claude/skills/azure-devops-pr-monthly/scripts/pr_metrics.py [Repository名稱] [統計天數, 預設 30]
```

## 預設參數設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| Organization | `isosoman0009` | 可透過 `AZURE_DEVOPS_ORG` 自訂 |
| Project | `dev` | 可透過 `AZURE_DEVOPS_PROJECT` 自訂 |
