---
name: azure-devops-patrol
description: |
  Azure DevOps 工作項目自動巡邏技能。當使用者提到「巡邏」、「patrol」、「Azure DevOps」、「DevOps 檢查」、「查看 issues」、「To Do 工作項目」等關鍵詞時請立即使用此技能。

  自動執行以下流程：
  1. 查詢 Azure DevOps 中 org=isosoman0009、project=dev、type=Issue、state=To Do 的所有工作項目
  2. 對每個找到的 work item 在 Discussion 留下帶時間戳的中文巡邏紀錄
  3. 將 work item 狀態更新為 Done

  只要使用者說「巡邏」、「幫我 patrol」、「跑一下 DevOps」、「檢查 Azure DevOps issues」，就應立即觸發此技能，無需使用者提供更多細節。
---

# Azure DevOps 巡邏技能

這個技能會自動巡邏 Azure DevOps 中待處理的 Issue 工作項目，留下巡邏紀錄並更新狀態。

## 前置條件

使用 `az devops` CLI，需要設定 PAT 環境變數：

```bash
export AZURE_DEVOPS_EXT_PAT="your_personal_access_token"
```

> 注意：az devops 用的是 `AZURE_DEVOPS_EXT_PAT`（非 `AZ2URE_DEVOPS_PAT`）
> 取得 PAT：Azure DevOps → User Settings → Personal Access Tokens
> 需要權限：Work Items (Read, Write & Manage)

extension 確認：`az extension list --query "[?name=='azure-devops']"`
若未安裝：`az extension add --name azure-devops`

## 執行步驟

1. **執行巡邏腳本**：

```bash
bash .claude/skills/azure-devops-patrol/scripts/patrol.sh
```

2. **回報結果**：根據腳本輸出，向使用者說明：
   - 找到幾個符合條件的 work items
   - 每個 work item 的 ID 和標題
   - 是否成功留下 comment 並更新狀態
   - 有無錯誤

## 目標設定

| 參數 | 值 |
|------|-----|
| Organization | `isosoman0009` |
| Project | `dev` |
| Work Item Type | Issue |
| 篩選狀態 | To Do |
| 更新後狀態 | Done |

## 回報格式

```
✅ 巡邏完成！
找到 3 個待處理 Issues：
- #42: 修正登入頁面錯誤 → 已留下紀錄，狀態更新為 Done
- #55: API timeout 問題 → 已留下紀錄，狀態更新為 Done
- #61: 手機版排版異常 → 已留下紀錄，狀態更新為 Done
```

若沒有找到任何 work items，告訴使用者「目前沒有待巡邏的 Issues，一切正常！」

## 錯誤處理

- **未登入（az account show 失敗）**：提示執行 `az login`
- **extension 未安裝**：提示 `az extension add --name azure-devops`
- **狀態更新失敗（400）**：`Done` 可能不是此 project 的有效狀態名稱，建議使用者至 Azure DevOps Project Settings → Process → Work Item Types 確認狀態
- **權限不足（403）**：確認 Azure 帳號有該 project 的 Contributor 以上權限
