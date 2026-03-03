---
name: legacy-code-analyzer
description: |
  分析舊有 VB6 或 VB.NET/C# 專案，自動生成 HTML 技術文件報告，包含 UI 說明、資料庫操作、業務邏輯與模組函式索引。

  使用時機：當使用者想了解舊專案邏輯、整理 VB6 或 .NET 程式碼文件、準備進行程式移轉、或讓新進員工快速了解舊系統時，立即使用此技能。不需要使用者說「分析」這個詞，只要使用者指向一個資料夾並說想了解或整理它的內容，就立即觸發。

  觸發關鍵詞：「分析專案」、「整理文件」、「看這個 VB6」、「舊專案」、「程式移轉文件」、「legacy」、「VB6」、「舊系統」、「幫我看這個專案」、「analyze this project」、「document this codebase」、「explain this old code」、「這個專案在幹嘛」。
---

# Legacy Code Analyzer

分析 VB6 / VB.NET / C# 舊專案，輸出 HTML 技術文件，幫助新人快速上手或準備程式移轉。

---

## 一、確認分析目標

如果使用者已提供資料夾路徑，直接進行。否則詢問：「請提供要分析的專案資料夾路徑。」

確認資料夾存在後，繼續下一步。

---

## 二、掃描專案結構

先全面了解專案的組成，再決定怎麼讀：

1. **偵測專案類型**：
   - 找到 `.vbp` → VB6 專案
   - 找到 `.vbproj` → VB.NET 專案
   - 找到 `.csproj` → C# 專案
   - 以上都有 → 混合專案

2. **列出所有原始碼檔案**：
   - VB6：`.frm`、`.bas`、`.cls`
   - VB.NET：`.vb`（排除 `.designer.vb`）
   - C#：`.cs`（排除 `.designer.cs`、`AssemblyInfo.cs`、`Program.cs` 這類骨架檔案）

3. **記錄統計數字**：各類型檔案數量，方便在報告開頭呈現。

> 如果原始碼檔案超過 30 個，先讀專案檔取得結構，再優先讀 Form/畫面相關的檔案，其餘模組選最有代表性的讀。在報告中說明哪些部分未完整分析。

---

## 三、逐步讀取與分析

依此順序讀取，同時持續整理四類資訊（見下方）：

1. **專案檔** (`.vbp` / `.vbproj` / `.csproj`)：了解整體結構與引用
2. **Form 檔** (`.frm` / 含 UI 邏輯的 `.vb`/`.cs`)：UI 說明
3. **模組與類別** (`.bas`、`.cls`、非 UI 的 `.vb`/`.cs`)：業務邏輯

---

### 收集四類資訊

#### A. UI / 表單說明

對每個 Form 記錄：

- **Form 名稱**與**視窗標題**（Caption）
- **主要控制項**：按鈕 (CommandButton/Button)、下拉 (ComboBox)、清單 (ListBox)、文字框 (TextBox)、資料格 (DataGrid/DataGridView) 等，記錄其名稱 (Name) 與顯示文字 (Caption/Text)
- **重要事件處理**：Form_Load 做了什麼、按鈕點擊觸發什麼動作
- **整體用途**：這個表單是給使用者做什麼用的（一兩句話）

**VB6 .frm 閱讀提示**：
- 控制項定義在 `Begin VB.CommandButton ... End` 區塊，`Caption` 是顯示文字，`Name` 是程式碼名稱
- 事件名稱格式：`Private Sub 控制項名稱_事件名()`，如 `Private Sub btnSave_Click()`

**VB.NET / C# 提示**：
- UI 控制項可能在 `.designer.vb`/`.designer.cs`，但業務邏輯在主 `.vb`/`.cs`
- 找 `_Click`、`_Load`、`_SelectedIndexChanged`、`_TextChanged` 等事件

---

#### B. 資料庫操作

找出所有資料庫相關的操作：

- **SQL 字串**：尋找 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`EXEC`、預存程序呼叫（`sp_` 開頭）
- **Table 名稱**：從 SQL 的 `FROM`、`JOIN`、`INTO`、`UPDATE` 後方提取
- **連線資訊**：Connection String、資料來源設定（不輸出密碼，只記錄連到哪個資料庫）
- **操作位置**：這個 SQL 在哪個模組 / 函式裡被使用，讓讀者知道誰在查哪張表

VB6 常見模式：`Dim rs As Recordset`、`rs.Open "SELECT ..."`
VB.NET 常見模式：`SqlCommand`、`OleDbCommand`、`DataAdapter`

---

#### C. 業務邏輯

找出重要的規則和計算，重點是「這在做什麼」，不是翻譯程式碼：

- **金融 / 數量計算**：稅率、折扣、加總、費率等計算公式
- **流程控制**：複雜的 If/Select Case、狀態判斷、驗證規則
- **重要常數**：`Const` 定義的固定值（規則、代碼含義等）
- **關鍵函式**：超過 20 行、邏輯複雜的函式，說明它在做什麼、為什麼

如果某段邏輯真的看不懂，誠實標記「⚠️ 邏輯待確認」，不要猜測。

---

#### D. 模組與函式索引

列出所有 Public / Friend 的函式和方法，格式：
- 函式名稱、所在模組、用途摘要（一句話）

---

## 四、生成 HTML 報告

把所有分析結果整合成一份 HTML 文件，儲存到專案資料夾：
**檔名**：`[專案資料夾名稱]_analysis_[YYYYMMDD].html`

### 視覺設計

- **佈局**：左側固定導覽列（220px），右側主內容可捲動
- **配色**：深藍側欄 (`#1e3a5f`)、白底主內容、標題藍 (`#2c5282`)
- **Section 標題**：帶左側藍色色條（`border-left: 4px solid #3182ce`）
- **SQL 程式碼**：`<pre><code>` 格式，淺灰底 (`#f7fafc`)
- **表格**：交替列背景（斑馬紋），用於函式索引和 Table 清單
- **導覽**：點擊側欄連結平滑捲動至對應 Section

### HTML 骨架

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[專案名稱] 程式碼分析報告</title>
  <style>
    body { margin: 0; font-family: 'Segoe UI', sans-serif; display: flex; }
    .sidebar { width: 220px; position: fixed; height: 100vh; background: #1e3a5f;
               overflow-y: auto; padding: 20px 0; }
    .sidebar a { display: block; color: #a0c4ff; padding: 8px 20px; text-decoration: none;
                 font-size: 0.88rem; }
    .sidebar a:hover { background: #2d5986; color: white; }
    .sidebar .group-label { color: #6fa8dc; font-size: 0.75rem; text-transform: uppercase;
                             padding: 12px 20px 4px; letter-spacing: 0.05em; }
    .content { margin-left: 220px; padding: 40px; max-width: 900px; }
    h1 { color: #1e3a5f; border-bottom: 2px solid #3182ce; padding-bottom: 10px; }
    h2 { color: #2c5282; border-left: 4px solid #3182ce; padding-left: 12px; margin-top: 40px; }
    h3 { color: #2d5986; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th { background: #2c5282; color: white; padding: 8px 12px; text-align: left; }
    td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
    tr:nth-child(even) td { background: #f7fafc; }
    pre { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 4px;
          padding: 12px; overflow-x: auto; font-size: 0.85rem; }
    code { font-family: 'Consolas', monospace; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
             font-size: 0.78rem; font-weight: bold; }
    .badge-vb6 { background: #fefcbf; color: #744210; }
    .badge-net { background: #c3dafe; color: #2b6cb0; }
    .warn { background: #fffbeb; border-left: 4px solid #f6ad55; padding: 10px 14px;
            margin: 12px 0; border-radius: 0 4px 4px 0; }
    .overview-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }
    .stat-card { background: #ebf8ff; border-radius: 8px; padding: 16px; text-align: center; }
    .stat-card .num { font-size: 2rem; font-weight: bold; color: #2c5282; }
    .stat-card .label { font-size: 0.8rem; color: #4a5568; }
  </style>
</head>
<body>
  <nav class="sidebar">
    <div style="color:white;font-weight:bold;padding:16px 20px;font-size:1rem;">
      [專案名稱]
    </div>
    <div class="group-label">導覽</div>
    <a href="#overview">📋 專案概覽</a>
    <a href="#ui">🖥️ 表單與 UI</a>
    <a href="#database">🗄️ 資料庫操作</a>
    <a href="#logic">⚙️ 業務邏輯</a>
    <a href="#modules">📚 函式索引</a>
    <div class="group-label" style="margin-top:20px;">表單</div>
    <!-- 每個 Form 一個連結 -->
    <a href="#form-XXX">XXX</a>
  </nav>

  <main class="content">
    <h1>[專案名稱] 程式碼分析報告</h1>
    <p style="color:#718096;">分析日期：[YYYY-MM-DD] ｜ 分析工具：Legacy Code Analyzer</p>

    <!-- Section 1: 概覽 -->
    <section id="overview">
      <h2>📋 專案概覽</h2>
      <p><strong>專案路徑：</strong>[路徑]</p>
      <p><strong>專案類型：</strong><span class="badge badge-vb6">VB6</span> / <span class="badge badge-net">VB.NET</span></p>
      <div class="overview-grid">
        <div class="stat-card"><div class="num">[N]</div><div class="label">表單數</div></div>
        <div class="stat-card"><div class="num">[N]</div><div class="label">模組數</div></div>
        <div class="stat-card"><div class="num">[N]</div><div class="label">SQL 查詢數</div></div>
        <div class="stat-card"><div class="num">[N]</div><div class="label">公開函式數</div></div>
      </div>
    </section>

    <!-- Section 2: UI -->
    <section id="ui">
      <h2>🖥️ 表單與 UI 說明</h2>
      <!-- 每個 Form 一個子區塊 -->
      <div id="form-XXX">
        <h3>frmXXX — [視窗標題]</h3>
        <p><strong>用途：</strong>[一兩句說明這個表單的功能]</p>
        <h4>主要控制項</h4>
        <table>
          <tr><th>控制項名稱</th><th>類型</th><th>功能說明</th></tr>
          <!-- 每個控制項一列 -->
        </table>
        <h4>重要事件</h4>
        <ul>
          <li><strong>Form_Load：</strong>[說明初始化做了什麼]</li>
          <li><strong>btnXXX_Click：</strong>[說明按鈕行為]</li>
        </ul>
      </div>
    </section>

    <!-- Section 3: Database -->
    <section id="database">
      <h2>🗄️ 資料庫操作</h2>
      <h3>使用到的資料表</h3>
      <table>
        <tr><th>Table 名稱</th><th>操作類型</th><th>所在位置</th><th>說明</th></tr>
        <!-- 每個 Table 一列 -->
      </table>
      <!-- 重要 SQL 查詢展示 -->
      <h3>重要查詢</h3>
      <h4>[查詢用途說明]（位於 [模組名.函式名]）</h4>
      <pre><code>SELECT ... FROM ... WHERE ...</code></pre>
    </section>

    <!-- Section 4: Business Logic -->
    <section id="logic">
      <h2>⚙️ 業務邏輯</h2>
      <!-- 依主題分組 -->
      <h3>[邏輯主題，如：費用計算]</h3>
      <p><strong>位於：</strong>[模組名.函式名]</p>
      <p>[說明這段邏輯在做什麼，為什麼]</p>
    </section>

    <!-- Section 5: Module Index -->
    <section id="modules">
      <h2>📚 模組與函式索引</h2>
      <table>
        <tr><th>函式名稱</th><th>所在模組</th><th>類型</th><th>說明</th></tr>
        <!-- 每個函式一列 -->
      </table>
    </section>
  </main>

  <script>
    // 平滑捲動
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
      });
    });
  </script>
</body>
</html>
```

---

## 五、完成回報

生成完畢後告知使用者：

```
✅ 分析完成！

專案：[專案名稱]
類型：[VB6 / VB.NET / C# / 混合]
分析範圍：[X] 個表單、[Y] 個模組、[Z] 個 SQL 查詢、[W] 個公開函式
報告位置：[完整路徑]/[專案名稱]_analysis_YYYYMMDD.html

在瀏覽器開啟 HTML 檔案即可查看完整文件。
```

---

## 注意事項

- **重點是說明「在做什麼」**，不是逐行翻譯程式碼。讀者是技術人員，能看懂程式；他們需要的是「這段邏輯的商業含義是什麼」。
- **如果看不懂**某段邏輯，誠實標記 `⚠️ 邏輯待確認`，不要猜測。
- **說明文字優先用繁體中文**，函式名、變數名、SQL 保留原文。
- 這份文件的最終讀者可能是未來要**移轉程式**的開發者，請確保他們能從報告中了解每個 Form 的目的、每個重要查詢的作用，以及核心業務規則。
