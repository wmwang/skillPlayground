---
name: azure-ai-requirements
description: |
  自動分析 Azure DevOps [AI] 需求工作項目，生成需求文件三件套的技能。當使用者提到「requirements」、「需求分析」、「跑 requirements」、「處理需求單」、「[AI] 需求」、「ai requirements」、「幫我分析需求」、「寫需求文件」等關鍵詞時，立即使用此技能，無需等待更多細節。

  自動流程：
  1. 在 org=isosoman0009, project=ai 中找出 title 含 [AI]、state=To Do、activity=Requirements、且有 Branch 的最新工作項目
  2. Clone 該 branch，讀取程式碼，理解現有架構
  3. 根據工作項目 Description 生成三份需求文件：
     - proposal.md（做什麼 & 為什麼）
     - design.md（怎麼做）
     - tasks.md（具體實作步驟）
  4. 將三份文件各自以 Discussion 留言方式貼到 ADO 工作項目
  5. 留下摘要 Discussion 紀錄，並將狀態更新為 Done
---

# Azure AI Requirements

這個技能讓 Claude 自動找到 Azure DevOps 中的 `[AI]` 需求工單，深度閱讀程式碼後，產出 proposal / design / tasks 三份文件，並直接回饋到 ADO Discussion。

## 前置條件

環境變數必須已設定：
```bash
export ADO_PAT="your_personal_access_token"   # 必填
export ADO_ORG="isosoman0009"                 # 選填，預設 isosoman0009
export ADO_PROJECT="ai"                       # 選填，預設 ai
export HTTP_PROXY="http://proxy.corp:8080"    # 選填，企業 proxy 環境使用
```

PAT 需要有：Work Items (Read, Write)、Code (Read) 的權限。

> **企業環境注意**：腳本自動偵測 `HTTP_PROXY` / `HTTPS_PROXY` 並套用，SSL 憑證驗證會自動 bypass。

---

## 完整執行流程

### Step 1：找到目標工作項目

```bash
python .claude/skills/azure-ai-requirements/scripts/find_work_item.py
```

**輸出格式（成功）：**
```json
{
  "found": true,
  "work_item_id": 55,
  "title": "[AI] 新增用戶登入功能",
  "description": "需要實作一個 JWT-based 登入流程，包含 /login endpoint ...",
  "branch": "feature/user-login",
  "repo_name": "myapp",
  "clone_url": "https://isosoman0009@dev.azure.com/isosoman0009/ai/_git/myapp",
  "default_branch": "main"
}
```

**若 `found` 為 false**：告知使用者目前沒有符合條件的工作項目，流程結束。

---

### Step 2：Clone 並探索程式碼

從 Step 1 取得 `clone_url`、`branch`，執行：

```bash
WORK_DIR=$(mktemp -d -t ai-req-XXXXXX)
echo "Working in: $WORK_DIR"

AUTH_URL=$(echo "<clone_url>" | sed "s|https://[^@]*@|https://pat:${ADO_PAT}@|")
git clone "$AUTH_URL" "$WORK_DIR"
cd "$WORK_DIR"
git checkout <branch>
```

> 如果 clone_url 沒有 `@`，直接用 `https://pat:${ADO_PAT}@dev.azure.com/...` 格式。

Clone 完成後，**仔細閱讀程式碼**，理解現有架構：
- 專案結構（目錄組織、主要模組）
- 相關的現有程式碼（會被這個需求影響到的部分）
- 技術棧（語言、框架、資料庫）
- 現有的 API / 接口設計慣例

這步驟很重要：文件的品質取決於你對現有 codebase 的理解深度。

---

### Step 3：生成三份需求文件

根據 Step 1 的 `description` 和 Step 2 的 codebase 理解，在 `$WORK_DIR` 生成：

#### 3a. proposal.md — 做什麼 & 為什麼

回答：這個需求的本質是什麼？背後的動機？範圍界定？成功標準？

```markdown
# Proposal: <需求標題>

## 背景
<說明為什麼需要這個功能，業務或技術背景>

## 目標
<具體要達成什麼，用戶/系統會得到什麼>

## 範圍
- **包含**：<在這次實作範圍內的事項>
- **不包含**：<明確排除在外的事項（避免範圍膨脹）>

## 成功標準
<可驗證的完成條件，例如「/login endpoint 返回 200 並附帶 JWT token」>

## 潛在風險
<技術或業務上的挑戰，需要注意的地方>
```

#### 3b. design.md — 怎麼做

根據 codebase 的現有架構，說明技術實作方式：

```markdown
# Design: <需求標題>

## 架構概覽
<用文字或簡單 ASCII 圖說明涉及的元件關係>

## 技術選型
<關鍵的技術決策和理由，例如選擇哪個 library、為什麼用這個 pattern>

## 主要變更
<哪些檔案/模組需要新增或修改，以及怎麼修改>

## 介面設計
<API endpoint、資料結構、function signature 等>

## 資料流程
<請求從進來到回應的完整流程>

## 考量與取捨
<設計中的妥協點和原因>
```

#### 3c. tasks.md — 實作步驟

把工作拆成開發者可以直接認領的具體 task：

```markdown
# Tasks: <需求標題>

## 實作清單

- [ ] **Task 1**: <具體的實作工作，指到特定檔案/函數>
  - 細節：<補充說明或注意事項>
- [ ] **Task 2**: <下一個工作>
  ...

## 測試清單

- [ ] 單元測試：<測什麼>
- [ ] 整合測試：<測什麼>
- [ ] 手動驗證：<驗證步驟>

## 備注
<開發者開始前需要知道的額外資訊>
```

---

### Step 4：將三份文件貼到 Discussion

執行腳本，把三份文件各自以一則 Discussion 留言貼上：

```bash
python .claude/skills/azure-ai-requirements/scripts/post_artifacts.py \
  <work_item_id> \
  "$WORK_DIR/proposal.md" \
  "$WORK_DIR/design.md" \
  "$WORK_DIR/tasks.md" \
  "<一句話說明本次處理的需求概要>"
```

腳本會：
1. 貼出 proposal.md 留言（帶標題「📋 Proposal」）
2. 貼出 design.md 留言（帶標題「🏗️ Design」）
3. 貼出 tasks.md 留言（帶標題「✅ Tasks」）
4. 貼出摘要留言並更新狀態為 Done

---

### Step 5：清理

```bash
rm -rf "$WORK_DIR"
echo "Done! Work item #<work_item_id> is now Done."
```

---

## 回報格式

完成後告訴使用者：

```
✅ AI Requirements 完成！

工作項目：#55 - [AI] 新增用戶登入功能
分析摘要：<一句話說明做了什麼分析>
生成文件：proposal.md / design.md / tasks.md
狀態：已更新為 Done
```

---

## 文件品質原則

- **proposal.md**：聚焦「為什麼」，讓不懂技術的人也能理解需求的價值
- **design.md**：緊扣現有 codebase，不要設計孤立的方案，要融入現有架構
- **tasks.md**：每個 task 應該是 1-2 天可完成的工作量，不要太粗也不要太細
- 文件語言：若 description 是中文就用中文，若是英文就用英文，跟 work item 保持一致

---

## 常見錯誤處理

| 情況 | 處理方式 |
|------|---------|
| `ADO_PAT` 未設定 | 提示使用者 `export ADO_PAT=<your_pat>` |
| 沒有符合條件的工作項目 | 告知使用者，流程結束 |
| git clone 失敗（403） | PAT 缺少 Code 讀取權限，請使用者確認 PAT 權限 |
| Description 內容不夠清楚 | 根據現有 codebase 做合理推斷，並在 Discussion 中說明假設 |
| 狀態更新失敗（400） | `Done` 可能不是此 project 的有效狀態，確認 Project Settings → Process |
