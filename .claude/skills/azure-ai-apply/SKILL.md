---
name: azure-ai-apply
description: |
  自動執行 Azure DevOps [ai] 工作項目的開發任務技能。當使用者提到「auto worker」、「跑 auto」、「執行 auto 工單」、「處理 [ai] 任務」、「ai task」、「自動執行工單」等關鍵詞時，立即使用此技能，無需等待更多細節。

  自動流程：
  1. 在 org=isosoman0009, project=ai 中找出 title 含 [ai]、state=To Do、activity=Development、且 Development 有 Branch 的最新工作項目
  2. Clone 該 branch，從它建立一個新的 auto branch
  3. 根據工作項目 Description 的任務說明進行程式碼修改
  4. Commit + Push，建立 PR merge 回原本的 work item branch
  5. 在 Discussion 留下執行紀錄，並將狀態更新為 Done
---

# Azure AI Apply

這個技能讓 Claude 自動找到並執行 Azure DevOps 中標記為 `[ai]` 的開發任務。

## 前置條件

環境變數必須已設定：
```bash
export ADO_PAT="your_personal_access_token"   # 必填
export ADO_ORG="isosoman0009"                 # 選填，預設 isosoman0009
export ADO_PROJECT="ai"                      # 選填，預設 dev
export HTTP_PROXY="http://proxy.corp:8080"    # 選填，企業 proxy 環境使用
```
PAT 需要有：Work Items (Read, Write)、Code (Read, Write)、Pull Requests (Read, Write) 的權限。

> **企業環境注意**：腳本會自動偵測 `HTTP_PROXY` / `HTTPS_PROXY` 並套用，同時 SSL 憑證驗證會自動 bypass，適用於企業內部 proxy/自簽憑證環境。

## 完整執行流程

### Step 1：找到目標工作項目

執行以下腳本，它會查詢符合條件的最新工作項目並輸出 JSON：

```bash
python .claude/skills/azure-ai-apply/scripts/find_work_item.py
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

### Step 1.5：檢查是否有 SDD 文件（Design Documents）

`azure-ai-requirements` 技能會在 Discussion 留下三份設計文件（Proposal / Design / Tasks）。腳本會依序在兩個地方尋找 SDD：

1. **Development 工單本身**的 Discussion（直接貼的情況）
2. **透過 parent link 找 Requirements 兄弟節點**：Development 和 Requirements 工單通常掛在同一個 parent（Feature / User Story）下，SDD 文件貼在 Requirements 工單的 Discussion 裡

這樣可以精確對應正確的設計文件，不會誤抓到其他不相關的 [AI] 工單。

```bash
python .claude/skills/azure-ai-apply/scripts/fetch_sdd.py <work_item_id>
```

**有 SDD 時（`"found": true`）：**
```json
{
  "found": true,
  "source_id": 55,
  "source": "requirements_sibling",
  "proposal": "需求背景...",
  "design": "技術設計方案...",
  "tasks": "## 實作清單\n- [ ] Task 1 ...\n- [ ] Task 2 ..."
}
```
→ 後續的 Step 3 改用 **SDD 模式**：以 `tasks` 清單作為工作項目、`design` 作為架構參考。

**沒有 SDD 時（`"found": false`）：**
→ 後續的 Step 3 用原本的 **Description 模式**：直接看 Step 1 的 `description` 欄位。

---

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

這樣做的原因：讓開發者有機會在 PR 上 review azure-ai-apply 的修改，而不是直接改動 feature branch。

### Step 3：理解並執行任務

根據 Step 1.5 的結果選擇模式：

#### 模式 A：SDD 模式（有設計文件）

從 `fetch_sdd.py` 的 `tasks` 欄位讀出工作清單，逐一完成：

1. **閱讀 `design`**：理解技術架構和主要變更方向，作為實作的設計參考
2. **解析 `tasks` 的工作清單**：找出所有 `- [ ]` 項目，依序執行
3. **逐 task 實作**：
   - 說明正在做哪一個 task
   - 在 `$WORK_DIR` 瀏覽相關程式碼，確認理解後再動手
   - 完成該 task 的程式碼修改
   - 繼續下一個 task
4. **若 task 描述不夠清楚**：根據 `design` 文件做合理推斷；若仍無法判斷，在 Discussion 中說明所做的假設

#### 模式 B：Description 模式（無設計文件，降級回原始行為）

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

### Step 5.5：執行測試並建立 Testing 工作項目

#### A. 取得原始工作項目的 Parent ID

使用 ADO REST API 查詢（不依賴 `az devops work-item`，避免環境相容性問題）：

```python
import urllib.request, json, os, ssl, base64

pat = os.environ.get('ADO_PAT', '')
token = base64.b64encode(f':{pat}'.encode()).decode()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://dev.azure.com/isosoman0009/ai/_apis/wit/workitems/<work_item_id>?$expand=relations&api-version=7.1'
req = urllib.request.Request(url, headers={'Authorization': f'Basic {token}'})
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.load(r)

parent_id = None
for rel in data.get('relations', []):
    if rel.get('rel') == 'System.LinkTypes.Hierarchy-Reverse':
        parent_id = rel['url'].split('/')[-1]
        break
# parent_id 為 None 代表無 parent，後續跳過掛 parent relation
```

若 `parent_id` 為 `None`（工作項目沒有 parent），後續仍建立工作項目，只是不掛 parent relation。

#### B. 偵測專案類型並執行測試

在 `$WORK_DIR` 中執行（此時程式碼已 commit，但 WORK_DIR 尚未清理）：

```bash
cd "$WORK_DIR"
TEST_OUTPUT_FILE=$(mktemp)

if ls pytest.ini setup.cfg pyproject.toml requirements.txt 2>/dev/null | head -1 | grep -q .; then
    python3 -m pytest --tb=short 2>&1 | tee "$TEST_OUTPUT_FILE"
    TEST_EXIT=${PIPESTATUS[0]}
    TEST_TYPE="pytest"
elif [ -f "package.json" ]; then
    npm test 2>&1 | tee "$TEST_OUTPUT_FILE"
    TEST_EXIT=${PIPESTATUS[0]}
    TEST_TYPE="npm test"
elif ls *.sln *.csproj 2>/dev/null | head -1 | grep -q .; then
    dotnet test 2>&1 | tee "$TEST_OUTPUT_FILE"
    TEST_EXIT=${PIPESTATUS[0]}
    TEST_TYPE="dotnet test"
else
    echo "無法偵測測試框架，略過執行" | tee "$TEST_OUTPUT_FILE"
    TEST_EXIT=0
    TEST_TYPE="none"
fi

TEST_STATUS=$( [ $TEST_EXIT -eq 0 ] && echo "PASSED" || echo "FAILED" )
TEST_SUMMARY=$(head -c 3000 "$TEST_OUTPUT_FILE")
```

#### C. 建立 Testing 工作項目、掛上 parent、並在 Discussion 寫入測試細節

全部使用 ADO REST API（python3）：

```python
import urllib.request, json, os, ssl, base64

pat = os.environ.get('ADO_PAT', '')
token = base64.b64encode(f':{pat}'.encode()).decode()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def ado_request(url, method, body=None, content_type='application/json-patch+json'):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': f'Basic {token}',
        'Content-Type': content_type,
    })
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.load(r)

# 1. 建立工作項目（Title + Activity，Description 留空，細節寫到 Discussion）
patch = [
    {'op': 'add', 'path': '/fields/System.Title',                    'value': '[test] <original_title>'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Common.Activity',  'value': 'Testing'},
]
result = ado_request(
    'https://dev.azure.com/isosoman0009/ai/_apis/wit/workitems/$Task?api-version=7.1',
    'POST', patch
)
new_item_id = result['id']

# 2. 掛上 parent（與原始工作項目同層）
if parent_id:
    rel_patch = [{
        'op': 'add',
        'path': '/relations/-',
        'value': {
            'rel': 'System.LinkTypes.Hierarchy-Reverse',
            'url': f'https://dev.azure.com/isosoman0009/ai/_apis/wit/workItems/{parent_id}',
        }
    }]
    ado_request(
        f'https://dev.azure.com/isosoman0009/ai/_apis/wit/workitems/{new_item_id}?api-version=7.1',
        'PATCH', rel_patch
    )

# 3. 在 Discussion 寫入測試細節（markdown 格式，ADO Discussion API 接收 HTML）
comment_html = f"""<h2>測試結果：{test_status}</h2>
<table>
<tr><td><strong>測試指令</strong></td><td>{test_type}</td></tr>
<tr><td><strong>對應 PR</strong></td><td><a href="{pr_url}">{pr_url}</a></td></tr>
<tr><td><strong>對應 Development 工單</strong></td><td>#{work_item_id}</td></tr>
</table>
<h3>測試輸出</h3>
<pre><code>{test_summary}</code></pre>"""

ado_request(
    f'https://dev.azure.com/isosoman0009/ai/_apis/wit/workitems/{new_item_id}/comments?api-version=7.1-preview.3',
    'POST', {'text': comment_html}, content_type='application/json'
)

print(f'Testing work item #{new_item_id} created with Discussion comment.')
```

> 即使測試失敗，流程仍繼續（自動化流程設計）。測試細節已以 markdown 格式記錄在 Testing 工作項目 `#new_item_id` 的 Discussion 中，供 PR reviewer 查閱。

---

### Step 6：記錄 Discussion 並更新狀態

執行收尾腳本，傳入 work_item_id、PR URL、以及一句話摘要：

```bash
python .claude/skills/azure-ai-apply/scripts/complete_task.py \
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
✅ Azure AI Apply 完成！

工作項目：#42 - [auto] 新增健康檢查 endpoint
執行內容：在 src/api.py 新增了 GET /health endpoint，回傳 {"status": "ok"}
Auto Branch：auto/42 → feature/auto-task-42
Pull Request：https://dev.azure.com/isosoman0009/dev/_git/dev/pullrequest/7
測試結果：PASSED（pytest）
Testing 工作項目：#43 - [test] [auto] 新增健康檢查 endpoint
狀態：已更新為 Done
```

---

## 常見錯誤處理

| 情況 | 處理方式 |
|------|---------|
| `ADO_PAT` 未設定 | 提示使用者 `export ADO_PAT=<your_pat>` |
| 沒有符合條件的工作項目 | 告知使用者，流程結束 |
| git clone 失敗（403） | PAT 缺少 Code 讀取權限，請使用者確認 PAT 權限 |
| PR 建立失敗（已存在） | 以 `az repos pr list` 找到現有 PR，繼續使用該 PR URL 執行 Step 6 |
| 狀態更新失敗（400） | `Done` 可能不是此 project 的有效狀態，確認 Project Settings → Process |
| az repos 找不到 extension | `az extension add --name azure-devops` |
| 找不到 parent ID（REST API 回傳無 Hierarchy-Reverse relation） | 跳過掛 parent relation，Testing 工作項目仍正常建立 |
| 測試框架偵測失敗 | 記錄「無法偵測測試框架」到 Discussion，流程繼續 |
| 建立 Testing 工作項目失敗（REST API 4xx/5xx） | 在 Step 6 的 Discussion 中補充說明測試結果，不阻斷主流程 |
| Discussion API 回傳 404（`comments` endpoint 不支援） | 改用 `_apis/wit/workitems/{id}` PATCH 更新 Description 欄位作為 fallback |
