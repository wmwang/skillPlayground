#!/bin/bash
# Azure DevOps 巡邏腳本 (az cli + PAT 版本)
#
# 前置條件：
#   az extension add --name azure-devops  （已安裝）
#   export AZURE_DEVOPS_EXT_PAT="your_pat"  （az devops 的 PAT env var）
#
# 使用方式：
#   bash .claude/skills/azure-devops-patrol/scripts/patrol.sh

set -euo pipefail

ORG_URL="https://dev.azure.com/isosoman0009"
PROJECT="dev"
TARGET_STATE="Done"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "🕐 巡邏開始 — $TIMESTAMP"
echo "📋 組織：isosoman0009  |  專案：$PROJECT"
echo "──────────────────────────────────────────────────"

# ── 確認 PAT 已設定 ──────────────────────────────────────────────────────────
if [ -z "${AZURE_DEVOPS_EXT_PAT:-}" ]; then
  echo "❌ 請先設定環境變數 AZURE_DEVOPS_EXT_PAT"
  echo "   取得方式：Azure DevOps → User Settings → Personal Access Tokens"
  echo "   需要權限：Work Items (Read, Write & Manage)"
  echo ""
  echo "   export AZURE_DEVOPS_EXT_PAT=\"your_token\""
  exit 1
fi

# ── 查詢符合條件的 work items ─────────────────────────────────────────────────
echo "🔍 查詢中：type=Issue、state=To Do …"

WIQL="SELECT [System.Id], [System.Title] FROM WorkItems \
WHERE [System.TeamProject] = '${PROJECT}' \
AND [System.WorkItemType] = 'Issue' \
AND [System.State] = 'To Do' \
ORDER BY [System.Id]"

QUERY_RESULT=$(az boards query \
  --wiql "$WIQL" \
  --org "$ORG_URL" \
  --project "$PROJECT" \
  -o json 2>&1) || {
    echo "❌ 查詢失敗：$QUERY_RESULT"
    exit 1
  }

# 解析 ID 清單
IDS=$(echo "$QUERY_RESULT" | python3 -c "
import json, sys
items = json.load(sys.stdin)
print('\n'.join(str(i['id']) for i in items))
" 2>/dev/null)

if [ -z "$IDS" ]; then
  echo "✅ 沒有找到待巡邏的 Issues，一切正常！"
  exit 0
fi

COUNT=$(echo "$IDS" | wc -l | tr -d ' ')
echo "📝 找到 $COUNT 個 work items"

SUCCESS=0
ERRORS=0

# 預先計算 Base64 PAT（curl 用）
PAT_B64=$(python3 -c "import base64, os; print(base64.b64encode(f\":{os.environ['AZURE_DEVOPS_EXT_PAT']}\".encode()).decode())")

# ── 處理每個 work item ────────────────────────────────────────────────────────
while IFS= read -r ID; do
  [ -z "$ID" ] && continue

  # 取得標題
  TITLE=$(az boards work-item show \
    --id "$ID" \
    --org "$ORG_URL" \
    --query "fields.\"System.Title\"" \
    -o tsv 2>/dev/null) || TITLE="(無法取得標題)"

  echo ""
  echo "  處理 #$ID: $TITLE"

  # 新增巡邏紀錄 comment（用 curl 直接呼叫 REST API，az devops invoke 對巢狀資源不可靠）
  COMMENT_JSON="{\"text\":\"<b>🔍 自動巡邏紀錄</b><br>巡邏時間：${TIMESTAMP}<br>此 Issue 已完成自動巡邏確認，狀態將更新為已完成（Done）。\"}"
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Basic $PAT_B64" \
    -H "Content-Type: application/json" \
    "${ORG_URL}/${PROJECT}/_apis/wit/workItems/${ID}/comments?api-version=7.1-preview.3" \
    -d "$COMMENT_JSON")

  if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "    ✅ 已新增巡邏紀錄 comment"
  else
    echo "    ❌ Comment 新增失敗（HTTP $HTTP_STATUS）"
    ERRORS=$((ERRORS + 1))
  fi

  # 更新狀態為 Done
  if az boards work-item update \
    --id "$ID" \
    --state "$TARGET_STATE" \
    --org "$ORG_URL" \
    -o none 2>/dev/null; then
    echo "    ✅ 狀態已更新為 $TARGET_STATE"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "    ❌ 狀態更新失敗（$TARGET_STATE 可能不是此專案的有效狀態名稱）"
    ERRORS=$((ERRORS + 1))
  fi

done <<< "$IDS"

echo ""
echo "════════════════════════════════════════════════"
echo "🎯 巡邏完成！成功：$SUCCESS 個｜失敗：$ERRORS 個"
