VERSION 5.00
Begin VB.Form frmProduct
   Caption         =   "商品資料"
   ClientHeight    =   4800
   ClientLeft      =   120
   ClientTop       =   450
   ClientWidth     =   5400
   LinkTopic       =   "Form2"
   ScaleHeight     =   4800
   ScaleWidth      =   5400
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton btnSave
      Caption         =   "儲存"
      Default         =   -1
      Height          =   375
      Left            =   3720
      TabIndex        =   8
      Top             =   4320
      Width           =   1575
   End
   Begin VB.CommandButton btnCancel
      Caption         =   "取消"
      Height          =   375
      Left            =   2040
      TabIndex        =   9
      Top             =   4320
      Width           =   1575
   End
   Begin VB.ComboBox cboCategory
      Height          =   315
      Left            =   1920
      TabIndex        =   2
      Top             =   960
      Width           =   3375
   End
   Begin VB.TextBox txtProductName
      Height          =   375
      Left            =   1920
      MaxLength       =   100
      TabIndex        =   1
      Top             =   480
      Width           =   3375
   End
   Begin VB.TextBox txtProductId
      Enabled         =   0
      Height          =   375
      Left            =   1920
      TabIndex        =   0
      Top             =   120
      Width           =   3375
   End
   Begin VB.TextBox txtStockQty
      Height          =   375
      Left            =   1920
      TabIndex        =   3
      Top             =   1440
      Width           =   1575
   End
   Begin VB.TextBox txtMinStock
      Height          =   375
      Left            =   1920
      TabIndex        =   4
      Top             =   1920
      Width           =   1575
   End
   Begin VB.TextBox txtUnitPrice
      Height          =   375
      Left            =   1920
      TabIndex        =   5
      Top             =   2400
      Width           =   1575
   End
   Begin VB.TextBox txtCostPrice
      Height          =   375
      Left            =   1920
      TabIndex        =   6
      Top             =   2880
      Width           =   1575
   End
   Begin VB.TextBox txtRemark
      Height          =   735
      Left            =   1920
      MultiLine       =   -1
      TabIndex        =   7
      Top             =   3360
      Width           =   3375
   End
End
Attribute VB_Name = "frmProduct"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

Public Mode As String       ' "ADD" 或 "EDIT"
Public ProductId As String
Public Updated As Boolean

Private Sub Form_Load()
    Updated = False

    ' 載入商品類別下拉選單
    Call LoadCategories

    If Mode = "EDIT" Then
        Me.Caption = "編輯商品資料"
        Call LoadProductData
    Else
        Me.Caption = "新增商品"
        ' 自動產生新商品編號
        txtProductId.Text = modDatabase.GetNextProductId()
    End If
End Sub

Private Sub LoadCategories()
    ' 從資料庫取得商品類別列表
    Dim rs As ADODB.Recordset
    Set rs = modDatabase.GetCategories()

    cboCategory.Clear
    Do While Not rs.EOF
        cboCategory.AddItem rs("CategoryName")
        rs.MoveNext
    Loop
    rs.Close
    Set rs = Nothing
End Sub

Private Sub LoadProductData()
    ' 載入現有商品資料進行編輯
    Dim rs As ADODB.Recordset
    Set rs = modDatabase.GetProductById(ProductId)

    If rs.EOF Then
        MsgBox "找不到商品資料", vbCritical
        Unload Me
        Exit Sub
    End If

    txtProductId.Text = rs("ProductID")
    txtProductName.Text = rs("ProductName")
    cboCategory.Text = rs("Category")
    txtStockQty.Text = rs("StockQty")
    txtMinStock.Text = rs("MinStock")
    txtUnitPrice.Text = rs("UnitPrice")
    txtCostPrice.Text = rs("CostPrice")
    txtRemark.Text = rs("Remark")

    rs.Close
    Set rs = Nothing
End Sub

Private Sub btnSave_Click()
    ' 輸入驗證
    If Trim(txtProductName.Text) = "" Then
        MsgBox "商品名稱不能空白", vbExclamation
        txtProductName.SetFocus
        Exit Sub
    End If

    If Not IsNumeric(txtUnitPrice.Text) Or CDbl(txtUnitPrice.Text) < 0 Then
        MsgBox "售價必須為有效數字", vbExclamation
        txtUnitPrice.SetFocus
        Exit Sub
    End If

    If Not IsNumeric(txtStockQty.Text) Or CInt(txtStockQty.Text) < 0 Then
        MsgBox "庫存數量必須為非負整數", vbExclamation
        txtStockQty.SetFocus
        Exit Sub
    End If

    ' 毛利率計算與警告
    Dim margin As Double
    If CDbl(txtUnitPrice.Text) > 0 And CDbl(txtCostPrice.Text) > 0 Then
        margin = (CDbl(txtUnitPrice.Text) - CDbl(txtCostPrice.Text)) / CDbl(txtUnitPrice.Text) * 100
        If margin < 10 Then
            Dim resp As Integer
            resp = MsgBox("此商品毛利率僅 " & Format(margin, "0.0") & "%，低於 10% 門檻，確定儲存？", vbQuestion + vbYesNo)
            If resp = vbNo Then Exit Sub
        End If
    End If

    ' 儲存資料
    Dim success As Boolean
    If Mode = "ADD" Then
        success = modDatabase.InsertProduct( _
            txtProductId.Text, txtProductName.Text, cboCategory.Text, _
            CInt(txtStockQty.Text), CInt(txtMinStock.Text), _
            CDbl(txtUnitPrice.Text), CDbl(txtCostPrice.Text), txtRemark.Text)
    Else
        success = modDatabase.UpdateProduct( _
            txtProductId.Text, txtProductName.Text, cboCategory.Text, _
            CInt(txtStockQty.Text), CInt(txtMinStock.Text), _
            CDbl(txtUnitPrice.Text), CDbl(txtCostPrice.Text), txtRemark.Text)
    End If

    If success Then
        Updated = True
        Unload Me
    Else
        MsgBox "儲存失敗，請稍後再試", vbCritical
    End If
End Sub

Private Sub btnCancel_Click()
    Updated = False
    Unload Me
End Sub
