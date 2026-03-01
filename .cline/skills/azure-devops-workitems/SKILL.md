---
name: azure-devops-workitems
description: Manage Azure DevOps Work Items end-to-end (query, create, update, transition state, assign, link, and bulk edits) via Azure CLI. Use this skill whenever the user mentions Azure DevOps Boards, work items, bugs, tasks, user stories, WIQL, sprint planning, backlog grooming, or asks to automate/update ticket fields—even if they do not explicitly ask for a "skill".
---

# Azure DevOps Work Items Skill

## Environment

- Auth is pre-configured. Do NOT run `az extension add` or `az login`.
- No `python3`. Use `--query` (JMESPath) + `-o tsv` for output parsing.

Set org/project defaults once per session if needed:
```bash
az devops configure --defaults organization=https://dev.azure.com/<org> project=<project>
```

---

## Valid commands (complete list — do not invent others)

```
az boards query          --wiql "<WIQL>" [--org <url>] [--project <proj>]
az boards work-item show --id <id>
az boards work-item create --type "<type>" --title "<title>" [--fields ...]
az boards work-item update --id <id> [--state <state>] [--assigned-to <email>] [--fields ...]
az boards work-item delete --id <id>
az boards work-item relation add    --id <id> --relation-type <type> --target-id <id>
az boards work-item relation remove --id <id> --relation-type <type> --target-id <id>
az boards work-item relation show   --id <id>
```

Commands that DO NOT EXIST:
- `az boards work-item list` / `az boards work-item query` / `az boards list`
- `az boards query --top` (no --top flag)

---

## Querying with WIQL

`az boards query` returns an **array**: `[{"id": 19, "fields": {...}}, ...]`

WIQL syntax: `SELECT [fields] FROM WorkItems [WHERE ...] [ORDER BY field DESC]`
- No `TOP n` in WIQL. Use JMESPath slice to limit: `--query "[:10]"`

```bash
# All IDs
az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems ORDER BY [System.ChangedDate] DESC" \
  --query "[].id" -o tsv

# First ID only
az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems ORDER BY [System.ChangedDate] DESC" \
  --query "[0].id" -o tsv
```

Guard against empty results before using the ID:
```bash
ITEM_ID=$(az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems ORDER BY [System.ChangedDate] DESC" \
  --query "[0].id" -o tsv 2>/dev/null)

if [ -z "$ITEM_ID" ] || [ "$ITEM_ID" = "None" ]; then
  echo "No matching work items found."
else
  az boards work-item show --id "$ITEM_ID"
fi
```

---

## Reading fields

Use double-quoted field names in `--query`:
```bash
az boards work-item show --id 19 \
  --query '{id:id, title:fields."System.Title", state:fields."System.State"}'
```

Common fields:
- `System.Title`, `System.State`, `System.AssignedTo`, `System.Tags`
- `System.AreaPath`, `System.IterationPath`
- `Microsoft.VSTS.Common.Priority`, `Microsoft.VSTS.Common.Severity`
- `Microsoft.VSTS.Scheduling.OriginalEstimate`
- `Microsoft.VSTS.Scheduling.RemainingWork`
- `Microsoft.VSTS.Scheduling.CompletedWork`

---

## Writing / mutating

Always preview what will change before executing, unless user says to skip preview.

```bash
# Create
az boards work-item create --type "Task" --title "fix login bug" \
  --fields "System.AssignedTo=alice@contoso.com" "System.IterationPath=dev\Sprint 1"

# Update
az boards work-item update --id 19 --state "Active" \
  --fields "System.Tags=hotfix" "Microsoft.VSTS.Common.Priority=1"

# Add parent link
az boards work-item relation add --id 20 --relation-type parent --target-id 19
```

After mutations, verify with `az boards work-item show --id <id>`.

---

## Example requests

- "把 Sprint 42 裡面指派給我的 Active bug 全部加上 hotfix tag"
- "建立 3 個 Task，掛在 User Story 12345 底下"
- "把 work item 5678 從 New 改成 Active，指派給 alice@contoso.com"
- "用 WIQL 找出過去 7 天新開的 P1 bug"
