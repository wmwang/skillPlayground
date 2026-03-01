---
name: azure-auto-worker
description: |
  自動執行 Azure DevOps [auto] 工作項目的開發任務技能。當使用者提到「auto worker」、「跑 auto」、「執行 auto 工單」、「處理 [auto] 任務」、「auto task」、「自動執行工單」等關鍵詞時，立即使用此技能，無需等待更多細節。

  自動流程：
  1. 在 org=isosoman0009, project=dev 中找出 title 含 [auto]、state=To Do、且 Development 有 Branch 的最新工作項目
  2. Clone 該 branch，從它建立一個新的 auto branch
  3. 根據工作項目 Description 的任務說明進行程式碼修改
  4. Commit + Push，建立 PR merge 回原本的 work item branch
  5. 在 Discussion 留下執行紀錄，並將狀態更新為 Done
---

# Azure Auto Worker

這個技能讓 Claude 自動找到並執行 Azure DevOps 中標記為 `[auto]` 的開發任務。

## 前置條件

環境變數必須已設定：
```bash
export AZURE_DEVOPS_EXT_PAT="your_personal_access_token"
```
PAT 需要有：Work Items (Read, Write)、Code (Read, Write)、Pull Requests (Read, Write) 的權限。

## 完整執行流程

### Step 1：找到目標工作項目

執行以下腳本，它會查詢符合條件的最新工作項目並輸出 JSON：

```bash
python .claude/skills/azure-auto-worker/scripts/find_work_item.py
```

**輸出格式（成功）：**
```json
{
  "found": true,
  "work_item_id": 42,
  "title": "[auto] 新增健康檢查 endpoint",
  "description": "在 src/api.py 第 30 行新增一個 GET /health endpoint，回傳 {\"status\": \"ok\"}",
  "branch": "feature/auto-task-42",
  "repo_name": "dev",
  "clone_url": "https://isosoman0009@dev.azure.com/isosoman0009/dev/_git/dev",
  "default_branch": "main"
}
```

**若 `found` 為 false**：告知使用者目前沒有符合條件的工作項目，流程結束。

### Step 2：Clone 並建立 auto branch

從 Step 1 取得 `clone_url`、`branch`（work item branch）、`work_item_id`，執行：

```bash
# 建立臨時工作目錄
WORK_DIR=$(mktemp -d -t auto-worker-XXXXXX)
echo "Working in: $WORK_DIR"

# Clone 並注入 PAT 認證
AUTH_URL=$(echo "<clone_url>" | sed "s|https://[^@]*@|https://pat:${AZURE_DEVOPS_EXT_PAT}@|")
git clone "$AUTH_URL" "$WORK_DIR"
cd "$WORK_DIR"

# 切換到 work item branch（這是任務的基礎）
git checkout <branch>

# 從 work item branch 建立新的 auto branch
# 命名慣例：auto/<work_item_id>
AUTO_BRANCH="auto/<work_item_id>"
git checkout -b "$AUTO_BRANCH"
```

> 如果 clone_url 沒有 `@`，直接用 `https://pat:${AZURE_DEVOPS_EXT_PAT}@dev.azure.com/...` 格式。

這樣做的原因：讓開發者有機會在 PR 上 review auto-worker 的修改，而不是直接改動 feature branch。

### Step 3：理解並執行任務

仔細閱讀 Step 1 輸出的 `description` 欄位，這是任務要求。

- 理解需要修改的檔案和內容
- 在 `$WORK_DIR` 目錄下瀏覽現有程式碼，確保了解現有結構再動手
- 根據 description 的要求進行修改

**處理方式的原則：**
- Description 是明確的技術任務（「在 X 檔案新增 Y 功能」）：直接執行
- Description 描述一個目標（「修正付款金額計算錯誤」）：先讀懂相關程式碼，找出問題再修改
- 若 description 不夠清楚：進行合理推斷，並在之後的 Discussion 中說明你做了什麼假設

### Step 4：Commit 並 Push auto branch

```bash
cd "$WORK_DIR"

# Stage 所有變更
git add -A

# Commit：根據實際做了什麼生成有意義的訊息
git commit -m "<feat/fix/chore>: <一句話描述改了什麼>"

# Push auto branch 到 origin
git push origin "$AUTO_BRANCH"
```

### Step 5：建立 Pull Request

PR 的方向是 **auto branch → work item branch**（不是 main），讓開發者可以 review：

```bash
az repos pr create \
  --org https://dev.azure.com/isosoman0009 \
  --project dev \
  --repository <repo_name> \
  --source-branch "$AUTO_BRANCH" \
  --target-branch <branch> \
  --title "<PR 標題：根據任務內容生成>" \
  --description "<PR 說明：簡述變更內容、影響範圍>" \
  --work-items <work_item_id> \
  --output json
```

從輸出取得 `pullRequestId` 和 PR 的 URL：
- PR URL 格式：`https://dev.azure.com/isosoman0009/dev/_git/<repo_name>/pullrequest/<pullRequestId>`

### Step 6：記錄 Discussion 並更新狀態

執行收尾腳本，傳入 work_item_id、PR URL、以及一句話摘要：

```bash
python .claude/skills/azure-auto-worker/scripts/complete_task.py \
  <work_item_id> \
  "<pr_url>" \
  "<一句話說明做了什麼，例如：在 src/api.py 新增了 GET /health endpoint>"
```

### Step 7：清理

```bash
rm -rf "$WORK_DIR"
echo "Done! Work item #<work_item_id> is now Done."
```

---

## 回報格式

完成後告訴使用者：

```
✅ Auto Worker 完成！

工作項目：#42 - [auto] 新增健康檢查 endpoint
執行內容：在 src/api.py 新增了 GET /health endpoint，回傳 {"status": "ok"}
Auto Branch：auto/42 → feature/auto-task-42
Pull Request：https://dev.azure.com/isosoman0009/dev/_git/dev/pullrequest/7
狀態：已更新為 Done
```

---

## 常見錯誤處理

| 情況 | 處理方式 |
|------|---------|
| `AZURE_DEVOPS_EXT_PAT` 未設定 | 提示使用者 `export AZURE_DEVOPS_EXT_PAT=<your_pat>` |
| 沒有符合條件的工作項目 | 告知使用者，流程結束 |
| git clone 失敗（403） | PAT 缺少 Code 讀取權限，請使用者確認 PAT 權限 |
| PR 建立失敗（已存在） | 以 `az repos pr list` 找到現有 PR，繼續使用該 PR URL 執行 Step 6 |
| 狀態更新失敗（400） | `Done` 可能不是此 project 的有效狀態，確認 Project Settings → Process |
| az repos 找不到 extension | `az extension add --name azure-devops` |
