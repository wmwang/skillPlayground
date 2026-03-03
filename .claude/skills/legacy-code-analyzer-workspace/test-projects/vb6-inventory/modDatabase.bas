Attribute VB_Name = "modDatabase"

' ====================================================
' 資料庫連線與操作模組
' ABC Corporation - 庫存管理系統
' 建立日期：2003/08/15
' 最後修改：2018/03/20
' ====================================================

Private Const CONN_STRING As String = "Provider=SQLOLEDB;Server=SRV-SQL01;Database=InventoryDB;UID=appuser;PWD=P@ssw0rd;"

Private g_Conn As ADODB.Connection

' 取得資料庫連線（單例模式）
Public Function GetConnection() As ADODB.Connection
    If g_Conn Is Nothing Then
        Set g_Conn = New ADODB.Connection
        g_Conn.ConnectionString = CONN_STRING
        g_Conn.CursorLocation = adUseClient
        g_Conn.Open
    ElseIf g_Conn.State = adStateClosed Then
        g_Conn.Open
    End If
    Set GetConnection = g_Conn
End Function

' 查詢商品清單（支援關鍵字搜尋）
Public Function GetProducts(keyword As String) As ADODB.Recordset
    Dim conn As ADODB.Connection
    Dim rs As ADODB.Recordset
    Set conn = GetConnection()
    Set rs = New ADODB.Recordset

    Dim sql As String
    If Trim(keyword) = "" Then
        sql = "SELECT ProductID, ProductName, Category, StockQty, MinStock, UnitPrice, CostPrice " & _
              "FROM Products " & _
              "WHERE IsDeleted = 0 " & _
              "ORDER BY Category, ProductName"
    Else
        sql = "SELECT ProductID, ProductName, Category, StockQty, MinStock, UnitPrice, CostPrice " & _
              "FROM Products " & _
              "WHERE IsDeleted = 0 " & _
              "  AND (ProductName LIKE '%" & keyword & "%' OR ProductID LIKE '%" & keyword & "%') " & _
              "ORDER BY Category, ProductName"
    End If

    rs.Open sql, conn, adOpenForwardOnly, adLockReadOnly
    Set GetProducts = rs
End Function

' 取得單一商品詳細資料
Public Function GetProductById(productId As String) As ADODB.Recordset
    Dim conn As ADODB.Connection
    Dim rs As ADODB.Recordset
    Set conn = GetConnection()
    Set rs = New ADODB.Recordset

    Dim sql As String
    sql = "SELECT * FROM Products WHERE ProductID = '" & productId & "' AND IsDeleted = 0"

    rs.Open sql, conn, adOpenStatic, adLockOptimistic
    Set GetProductById = rs
End Function

' 新增商品
Public Function InsertProduct(productId As String, productName As String, category As String, _
                               stockQty As Integer, minStock As Integer, _
                               unitPrice As Double, costPrice As Double, remark As String) As Boolean
    Dim conn As ADODB.Connection
    Set conn = GetConnection()

    Dim sql As String
    sql = "INSERT INTO Products (ProductID, ProductName, Category, StockQty, MinStock, UnitPrice, CostPrice, Remark, CreateDate, IsDeleted) " & _
          "VALUES ('" & productId & "', '" & productName & "', '" & category & "', " & _
          stockQty & ", " & minStock & ", " & unitPrice & ", " & costPrice & ", '" & remark & "', GETDATE(), 0)"

    On Error GoTo ErrHandler
    conn.Execute sql
    InsertProduct = True
    Exit Function

ErrHandler:
    InsertProduct = False
End Function

' 更新商品資料
Public Function UpdateProduct(productId As String, productName As String, category As String, _
                               stockQty As Integer, minStock As Integer, _
                               unitPrice As Double, costPrice As Double, remark As String) As Boolean
    Dim conn As ADODB.Connection
    Set conn = GetConnection()

    Dim sql As String
    sql = "UPDATE Products SET " & _
          "ProductName = '" & productName & "', " & _
          "Category = '" & category & "', " & _
          "StockQty = " & stockQty & ", " & _
          "MinStock = " & minStock & ", " & _
          "UnitPrice = " & unitPrice & ", " & _
          "CostPrice = " & costPrice & ", " & _
          "Remark = '" & remark & "', " & _
          "ModifyDate = GETDATE() " & _
          "WHERE ProductID = '" & productId & "'"

    On Error GoTo ErrHandler
    conn.Execute sql
    UpdateProduct = True
    Exit Function

ErrHandler:
    UpdateProduct = False
End Function

' 刪除商品（軟刪除）
Public Function DeleteProduct(productId As String) As Boolean
    Dim conn As ADODB.Connection
    Set conn = GetConnection()

    ' 使用軟刪除，保留歷史資料
    Dim sql As String
    sql = "UPDATE Products SET IsDeleted = 1, DeleteDate = GETDATE() WHERE ProductID = '" & productId & "'"

    On Error GoTo ErrHandler
    conn.Execute sql
    DeleteProduct = True
    Exit Function

ErrHandler:
    DeleteProduct = False
End Function

' 檢查商品是否有未完成訂單
Public Function HasPendingOrders(productId As String) As Boolean
    Dim conn As ADODB.Connection
    Dim rs As ADODB.Recordset
    Set conn = GetConnection()
    Set rs = New ADODB.Recordset

    Dim sql As String
    sql = "SELECT COUNT(*) AS cnt " & _
          "FROM OrderDetails od " & _
          "INNER JOIN Orders o ON od.OrderID = o.OrderID " & _
          "WHERE od.ProductID = '" & productId & "' " & _
          "  AND o.Status IN ('PENDING', 'PROCESSING')"

    rs.Open sql, conn, adOpenForwardOnly, adLockReadOnly
    HasPendingOrders = (rs("cnt") > 0)
    rs.Close
    Set rs = Nothing
End Function

' 取得商品類別清單
Public Function GetCategories() As ADODB.Recordset
    Dim conn As ADODB.Connection
    Dim rs As ADODB.Recordset
    Set conn = GetConnection()
    Set rs = New ADODB.Recordset

    rs.Open "SELECT CategoryName FROM Categories WHERE IsActive = 1 ORDER BY SortOrder", _
            conn, adOpenForwardOnly, adLockReadOnly
    Set GetCategories = rs
End Function

' 產生下一個商品編號（格式：P + 年份後兩碼 + 四位流水號，例如：P23-0001）
Public Function GetNextProductId() As String
    Dim conn As ADODB.Connection
    Dim rs As ADODB.Recordset
    Set conn = GetConnection()
    Set rs = New ADODB.Recordset

    Dim yearPart As String
    yearPart = Right(CStr(Year(Now)), 2)

    Dim sql As String
    sql = "SELECT MAX(ProductID) AS MaxID FROM Products WHERE ProductID LIKE 'P" & yearPart & "-%'"

    rs.Open sql, conn, adOpenForwardOnly, adLockReadOnly

    Dim nextNum As Integer
    If IsNull(rs("MaxID")) Then
        nextNum = 1
    Else
        nextNum = CInt(Right(rs("MaxID"), 4)) + 1
    End If

    GetNextProductId = "P" & yearPart & "-" & Format(nextNum, "0000")
    rs.Close
    Set rs = Nothing
End Function

' 調整庫存數量（進貨/出貨使用）
Public Function AdjustStock(productId As String, adjustQty As Integer, reason As String) As Boolean
    Dim conn As ADODB.Connection
    Set conn = GetConnection()

    On Error GoTo ErrHandler
    conn.BeginTrans

    ' 先查目前庫存
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open "SELECT StockQty FROM Products WHERE ProductID = '" & productId & "'", _
            conn, adOpenStatic, adLockOptimistic

    Dim currentQty As Integer
    currentQty = rs("StockQty")

    If currentQty + adjustQty < 0 Then
        MsgBox "庫存不足，無法扣減", vbExclamation
        conn.RollbackTrans
        AdjustStock = False
        Exit Function
    End If

    rs.Fields("StockQty") = currentQty + adjustQty
    rs.Update
    rs.Close

    ' 寫入庫存異動記錄
    conn.Execute "INSERT INTO StockHistory (ProductID, AdjustQty, BeforeQty, AfterQty, Reason, AdjustDate) " & _
                 "VALUES ('" & productId & "', " & adjustQty & ", " & currentQty & ", " & _
                 (currentQty + adjustQty) & ", '" & reason & "', GETDATE())"

    conn.CommitTrans
    AdjustStock = True
    Exit Function

ErrHandler:
    conn.RollbackTrans
    AdjustStock = False
End Function
