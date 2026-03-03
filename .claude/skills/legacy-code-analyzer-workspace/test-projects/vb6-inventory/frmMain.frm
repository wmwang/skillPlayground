VERSION 5.00
Begin VB.Form frmMain
   Caption         =   "庫存管理系統 v1.0"
   ClientHeight    =   6000
   ClientLeft      =   120
   ClientTop       =   450
   ClientWidth     =   9600
   LinkTopic       =   "Form1"
   ScaleHeight     =   6000
   ScaleWidth      =   9600
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton btnRefresh
      Caption         =   "重新整理"
      Height          =   375
      Left            =   7800
      TabIndex        =   5
      Top             =   240
      Width           =   1575
   End
   Begin VB.CommandButton btnDelete
      Caption         =   "刪除"
      Height          =   375
      Left            =   6000
      TabIndex        =   4
      Top             =   240
      Width           =   1575
   End
   Begin VB.CommandButton btnEdit
      Caption         =   "編輯"
      Height          =   375
      Left            =   4200
      TabIndex        =   3
      Top             =   240
      Width           =   1575
   End
   Begin VB.CommandButton btnAdd
      Caption         =   "新增商品"
      Height          =   375
      Left            =   120
      TabIndex        =   2
      Top             =   240
      Width           =   1575
   End
   Begin VB.TextBox txtSearch
      Height          =   375
      Left            =   2040
      TabIndex        =   1
      Text            =   ""
      Top             =   240
      Width           =   1935
   End
   Begin VB.Label lblSearch
      Caption         =   "搜尋商品："
      Height          =   255
      Left            =   1560
      TabIndex        =   0
      Top             =   285
      Width           =   975
   End
   Begin MSFlexGridLib.MSFlexGrid grdProducts
      Height          =   4800
      Left            =   120
      TabIndex        =   6
      Top             =   720
      Width           =   9360
      _ExtentX        =   16510
      _ExtentY        =   8467
      Rows            =   1
      Cols            =   6
   End
   Begin VB.Label lblStatus
      Caption         =   "就緒"
      Height          =   255
      Left            =   120
      TabIndex        =   7
      Top             =   5640
      Width           =   9360
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

Private Sub Form_Load()
    ' 設定表格標題
    With grdProducts
        .FixedRows = 1
        .Rows = 1
        .Cols = 6
        .ColWidth(0) = 1200
        .ColWidth(1) = 3000
        .ColWidth(2) = 1800
        .ColWidth(3) = 1800
        .ColWidth(4) = 1800
        .ColWidth(5) = 1500
        .TextMatrix(0, 0) = "商品編號"
        .TextMatrix(0, 1) = "商品名稱"
        .TextMatrix(0, 2) = "類別"
        .TextMatrix(0, 3) = "庫存數量"
        .TextMatrix(0, 4) = "售價"
        .TextMatrix(0, 5) = "狀態"
    End With

    ' 載入所有商品資料
    Call LoadProducts("")

    lblStatus.Caption = "系統就緒，共 " & (grdProducts.Rows - 1) & " 筆商品"
End Sub

Private Sub btnAdd_Click()
    ' 開啟新增商品表單
    Dim frm As New frmProduct
    frm.Mode = "ADD"
    frm.Show vbModal

    ' 重新載入清單
    If frm.Updated Then
        Call LoadProducts(txtSearch.Text)
    End If
    Unload frm
End Sub

Private Sub btnEdit_Click()
    ' 檢查是否選取了商品
    If grdProducts.Row = 0 Then
        MsgBox "請先選取一筆商品", vbExclamation
        Exit Sub
    End If

    Dim productId As String
    productId = grdProducts.TextMatrix(grdProducts.Row, 0)

    Dim frm As New frmProduct
    frm.Mode = "EDIT"
    frm.ProductId = productId
    frm.Show vbModal

    If frm.Updated Then
        Call LoadProducts(txtSearch.Text)
    End If
    Unload frm
End Sub

Private Sub btnDelete_Click()
    If grdProducts.Row = 0 Then
        MsgBox "請先選取一筆商品", vbExclamation
        Exit Sub
    End If

    Dim productId As String
    Dim productName As String
    productId = grdProducts.TextMatrix(grdProducts.Row, 0)
    productName = grdProducts.TextMatrix(grdProducts.Row, 1)

    ' 確認刪除
    Dim resp As Integer
    resp = MsgBox("確定要刪除商品「" & productName & "」嗎？此操作無法復原。", vbQuestion + vbYesNo)
    If resp = vbNo Then Exit Sub

    ' 檢查是否有未出貨的訂單使用此商品
    If modDatabase.HasPendingOrders(productId) Then
        MsgBox "此商品有未完成的訂單，無法刪除。請先處理相關訂單。", vbExclamation
        Exit Sub
    End If

    ' 執行刪除
    If modDatabase.DeleteProduct(productId) Then
        lblStatus.Caption = "商品「" & productName & "」已刪除"
        Call LoadProducts(txtSearch.Text)
    Else
        MsgBox "刪除失敗，請聯絡系統管理員", vbCritical
    End If
End Sub

Private Sub btnRefresh_Click()
    Call LoadProducts(txtSearch.Text)
End Sub

Private Sub txtSearch_Change()
    ' 即時搜尋：每次輸入都重新過濾
    Call LoadProducts(txtSearch.Text)
End Sub

Private Sub LoadProducts(keyword As String)
    Dim rs As ADODB.Recordset
    Set rs = modDatabase.GetProducts(keyword)

    ' 清空表格（保留標題列）
    grdProducts.Rows = 1

    If rs.EOF Then
        lblStatus.Caption = "找不到符合條件的商品"
        Exit Sub
    End If

    ' 填入資料
    Do While Not rs.EOF
        grdProducts.AddItem ""
        Dim row As Integer
        row = grdProducts.Rows - 1

        grdProducts.TextMatrix(row, 0) = rs("ProductID")
        grdProducts.TextMatrix(row, 1) = rs("ProductName")
        grdProducts.TextMatrix(row, 2) = rs("Category")
        grdProducts.TextMatrix(row, 3) = rs("StockQty")
        grdProducts.TextMatrix(row, 4) = Format(rs("UnitPrice"), "NT$#,##0")

        ' 庫存狀態判斷
        If rs("StockQty") = 0 Then
            grdProducts.TextMatrix(row, 5) = "無庫存"
        ElseIf rs("StockQty") <= rs("MinStock") Then
            grdProducts.TextMatrix(row, 5) = "庫存不足"
        Else
            grdProducts.TextMatrix(row, 5) = "正常"
        End If

        rs.MoveNext
    Loop

    lblStatus.Caption = "共 " & (grdProducts.Rows - 1) & " 筆商品"
    rs.Close
    Set rs = Nothing
End Sub
