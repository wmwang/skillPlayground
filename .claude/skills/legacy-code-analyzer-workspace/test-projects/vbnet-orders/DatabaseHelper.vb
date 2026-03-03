Imports System.Data.SqlClient
Imports System.Configuration

''' <summary>
''' 資料庫存取輔助類別
''' 封裝所有 SQL 操作，提供型別安全的資料存取方法
''' </summary>
Public Class DatabaseHelper

    Private ReadOnly _connectionString As String = ConfigurationManager.ConnectionStrings("OrderDB").ConnectionString

    ''' <summary>
    ''' 依篩選條件查詢訂單清單（分頁）
    ''' </summary>
    Public Function GetOrders(filter As OrderFilter) As OrderQueryResult
        Dim result As New OrderQueryResult()

        Using conn As New SqlConnection(_connectionString)
            conn.Open()

            ' 建立動態查詢條件
            Dim whereClauses As New List(Of String)()
            Dim cmd As New SqlCommand()
            cmd.Connection = conn

            whereClauses.Add("o.IsDeleted = 0")

            If Not String.IsNullOrEmpty(filter.CustomerKeyword) Then
                whereClauses.Add("(c.CustomerName LIKE @keyword OR c.CustomerCode LIKE @keyword)")
                cmd.Parameters.AddWithValue("@keyword", "%" & filter.CustomerKeyword & "%")
            End If

            If Not String.IsNullOrEmpty(filter.Status) Then
                whereClauses.Add("o.Status = @status")
                cmd.Parameters.AddWithValue("@status", filter.Status)
            End If

            If filter.DateFrom.HasValue Then
                whereClauses.Add("o.OrderDate >= @dateFrom")
                cmd.Parameters.AddWithValue("@dateFrom", filter.DateFrom.Value)
            End If

            If filter.DateTo.HasValue Then
                whereClauses.Add("o.OrderDate <= @dateTo")
                cmd.Parameters.AddWithValue("@dateTo", filter.DateTo.Value)
            End If

            Dim whereStr As String = String.Join(" AND ", whereClauses)

            ' 查詢總數
            cmd.CommandText = $"SELECT COUNT(*) FROM Orders o INNER JOIN Customers c ON o.CustomerID = c.CustomerID WHERE {whereStr}"
            result.TotalCount = CInt(cmd.ExecuteScalar())

            ' 查詢本頁訂單
            cmd.CommandText = $"
                SELECT o.OrderID, o.OrderDate, c.CustomerName,
                       o.TotalAmount, o.Status AS StatusName,
                       e.EmployeeName AS SalespersonName
                FROM Orders o
                INNER JOIN Customers c ON o.CustomerID = c.CustomerID
                INNER JOIN Employees e ON o.SalespersonID = e.EmployeeID
                WHERE {whereStr}
                ORDER BY o.OrderDate DESC, o.OrderID DESC
                OFFSET {(filter.Page - 1) * filter.PageSize} ROWS
                FETCH NEXT {filter.PageSize} ROWS ONLY"

            Dim adapter As New SqlDataAdapter(cmd)
            Dim dt As New DataTable()
            adapter.Fill(dt)
            result.Orders = dt

            ' 查詢篩選期間總金額（用於底部統計顯示）
            cmd.CommandText = $"SELECT ISNULL(SUM(o.TotalAmount), 0) FROM Orders o INNER JOIN Customers c ON o.CustomerID = c.CustomerID WHERE {whereStr}"
            result.TotalAmount = CDec(cmd.ExecuteScalar())
        End Using

        Return result
    End Function

    ''' <summary>
    ''' 取得訂單明細（含訂單主檔與明細行）
    ''' </summary>
    Public Function GetOrderDetail(orderId As String) As OrderDetailData
        Dim data As New OrderDetailData()

        Using conn As New SqlConnection(_connectionString)
            conn.Open()

            ' 訂單主檔
            Dim cmdHeader As New SqlCommand("
                SELECT o.*, c.CustomerName, c.CustomerAddress, c.TaxID,
                       e.EmployeeName AS SalespersonName, e.Phone AS SalespersonPhone
                FROM Orders o
                INNER JOIN Customers c ON o.CustomerID = c.CustomerID
                INNER JOIN Employees e ON o.SalespersonID = e.EmployeeID
                WHERE o.OrderID = @orderId", conn)
            cmdHeader.Parameters.AddWithValue("@orderId", orderId)

            Dim adapterH As New SqlDataAdapter(cmdHeader)
            Dim dtHeader As New DataTable()
            adapterH.Fill(dtHeader)
            data.Header = dtHeader

            ' 訂單明細行
            Dim cmdLines As New SqlCommand("
                SELECT od.LineNo, od.ProductID, p.ProductName, p.Unit,
                       od.Quantity, od.UnitPrice, od.Discount,
                       od.Quantity * od.UnitPrice * (1 - od.Discount / 100.0) AS LineTotal,
                       od.Remark
                FROM OrderDetails od
                INNER JOIN Products p ON od.ProductID = p.ProductID
                WHERE od.OrderID = @orderId
                ORDER BY od.LineNo", conn)
            cmdLines.Parameters.AddWithValue("@orderId", orderId)

            Dim adapterL As New SqlDataAdapter(cmdLines)
            Dim dtLines As New DataTable()
            adapterL.Fill(dtLines)
            data.Lines = dtLines
        End Using

        Return data
    End Function

    ''' <summary>
    ''' 取消訂單
    ''' </summary>
    Public Function CancelOrder(orderId As String, reason As String) As Boolean
        Using conn As New SqlConnection(_connectionString)
            conn.Open()
            Dim tran = conn.BeginTransaction()

            Try
                ' 更新訂單狀態
                Dim cmd1 As New SqlCommand("
                    UPDATE Orders SET Status = 'CANCELLED', CancelReason = @reason,
                           CancelDate = GETDATE(), UpdatedAt = GETDATE()
                    WHERE OrderID = @orderId AND Status IN ('PENDING', 'PROCESSING')", conn, tran)
                cmd1.Parameters.AddWithValue("@orderId", orderId)
                cmd1.Parameters.AddWithValue("@reason", reason)

                Dim affected As Integer = cmd1.ExecuteNonQuery()
                If affected = 0 Then
                    tran.Rollback()
                    Return False
                End If

                ' 退回庫存
                Dim cmd2 As New SqlCommand("
                    UPDATE p SET p.StockQty = p.StockQty + od.Quantity
                    FROM Products p
                    INNER JOIN OrderDetails od ON p.ProductID = od.ProductID
                    WHERE od.OrderID = @orderId", conn, tran)
                cmd2.Parameters.AddWithValue("@orderId", orderId)
                cmd2.ExecuteNonQuery()

                ' 寫入操作記錄
                Dim cmd3 As New SqlCommand("
                    INSERT INTO OrderLog (OrderID, Action, Remark, ActionDate, ActionBy)
                    VALUES (@orderId, 'CANCEL', @reason, GETDATE(), SYSTEM_USER)", conn, tran)
                cmd3.Parameters.AddWithValue("@orderId", orderId)
                cmd3.Parameters.AddWithValue("@reason", reason)
                cmd3.ExecuteNonQuery()

                tran.Commit()
                Return True
            Catch ex As Exception
                tran.Rollback()
                Return False
            End Try
        End Using
    End Function
End Class

' 資料傳輸物件（DTO）
Public Class OrderFilter
    Public Property CustomerKeyword As String
    Public Property Status As String
    Public Property DateFrom As Date?
    Public Property DateTo As Date?
    Public Property Page As Integer = 1
    Public Property PageSize As Integer = 50
End Class

Public Class OrderQueryResult
    Public Property Orders As DataTable
    Public Property TotalCount As Integer
    Public Property TotalAmount As Decimal
End Class

Public Class OrderDetailData
    Public Property Header As DataTable
    Public Property Lines As DataTable
End Class
