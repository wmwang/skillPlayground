Imports System.Windows.Forms
Imports System.Data.SqlClient

''' <summary>
''' 訂單查詢主畫面
''' 提供訂單清單瀏覽、狀態篩選、及訂單操作入口
''' </summary>
Public Class frmOrderList
    Inherits Form

    Private _db As New DatabaseHelper()
    Private _currentPage As Integer = 1
    Private Const PAGE_SIZE As Integer = 50

    ' 控制項宣告（對應 designer）
    Private WithEvents btnSearch As Button
    Private WithEvents btnNew As Button
    Private WithEvents btnEdit As Button
    Private WithEvents btnCancel As Button
    Private WithEvents btnPrint As Button
    Private WithEvents btnPrevPage As Button
    Private WithEvents btnNextPage As Button
    Private WithEvents cboStatus As ComboBox
    Private WithEvents dtpFrom As DateTimePicker
    Private WithEvents dtpTo As DateTimePicker
    Private WithEvents txtCustomer As TextBox
    Private WithEvents dgvOrders As DataGridView
    Private WithEvents lblTotalAmount As Label
    Private WithEvents lblPageInfo As Label

    Private Sub frmOrderList_Load(sender As Object, e As EventArgs) Handles Me.Load
        ' 初始化狀態下拉選單
        cboStatus.Items.AddRange(New String() {"全部", "待確認", "處理中", "已出貨", "已完成", "已取消"})
        cboStatus.SelectedIndex = 0

        ' 設定預設日期範圍（本月）
        dtpFrom.Value = New DateTime(Now.Year, Now.Month, 1)
        dtpTo.Value = Now.Date

        ' 設定 DataGridView 樣式
        ConfigureGrid()

        ' 載入訂單
        LoadOrders()
    End Sub

    Private Sub ConfigureGrid()
        dgvOrders.AutoGenerateColumns = False
        dgvOrders.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        dgvOrders.MultiSelect = False
        dgvOrders.ReadOnly = True
        dgvOrders.AllowUserToAddRows = False

        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colOrderId", .HeaderText = "訂單編號", .DataPropertyName = "OrderID", .Width = 120
        })
        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colOrderDate", .HeaderText = "訂單日期", .DataPropertyName = "OrderDate", .Width = 100,
            .DefaultCellStyle = New DataGridViewCellStyle() With {.Format = "yyyy/MM/dd"}
        })
        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colCustomer", .HeaderText = "客戶名稱", .DataPropertyName = "CustomerName", .Width = 200
        })
        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colAmount", .HeaderText = "訂單金額", .DataPropertyName = "TotalAmount", .Width = 120,
            .DefaultCellStyle = New DataGridViewCellStyle() With {.Format = "N0", .Alignment = DataGridViewContentAlignment.MiddleRight}
        })
        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colStatus", .HeaderText = "狀態", .DataPropertyName = "StatusName", .Width = 80
        })
        dgvOrders.Columns.Add(New DataGridViewTextBoxColumn() With {
            .Name = "colSalesperson", .HeaderText = "業務員", .DataPropertyName = "SalespersonName", .Width = 80
        })
    End Sub

    Private Sub LoadOrders()
        Dim filter As New OrderFilter() With {
            .CustomerKeyword = txtCustomer.Text.Trim(),
            .Status = If(cboStatus.SelectedIndex = 0, Nothing, cboStatus.SelectedItem.ToString()),
            .DateFrom = dtpFrom.Value.Date,
            .DateTo = dtpTo.Value.Date,
            .Page = _currentPage,
            .PageSize = PAGE_SIZE
        }

        Dim result = _db.GetOrders(filter)
        dgvOrders.DataSource = result.Orders

        ' 更新頁碼與統計
        lblPageInfo.Text = $"第 {_currentPage} 頁，共 {Math.Ceiling(result.TotalCount / PAGE_SIZE)} 頁（{result.TotalCount} 筆）"
        lblTotalAmount.Text = $"篩選期間總金額：NT$ {result.TotalAmount:N0}"

        btnPrevPage.Enabled = _currentPage > 1
        btnNextPage.Enabled = _currentPage * PAGE_SIZE < result.TotalCount
    End Sub

    Private Sub btnSearch_Click(sender As Object, e As EventArgs) Handles btnSearch.Click
        _currentPage = 1
        LoadOrders()
    End Sub

    Private Sub btnNew_Click(sender As Object, e As EventArgs) Handles btnNew.Click
        Dim frm As New frmOrderDetail(Nothing)
        If frm.ShowDialog() = DialogResult.OK Then
            LoadOrders()
        End If
    End Sub

    Private Sub btnEdit_Click(sender As Object, e As EventArgs) Handles btnEdit.Click
        If dgvOrders.SelectedRows.Count = 0 Then
            MessageBox.Show("請先選取一筆訂單", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information)
            Return
        End If

        Dim orderId As String = dgvOrders.SelectedRows(0).Cells("colOrderId").Value.ToString()
        Dim frm As New frmOrderDetail(orderId)
        If frm.ShowDialog() = DialogResult.OK Then
            LoadOrders()
        End If
    End Sub

    Private Sub btnCancel_Click(sender As Object, e As EventArgs) Handles btnCancel.Click
        If dgvOrders.SelectedRows.Count = 0 Then
            MessageBox.Show("請先選取一筆訂單", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information)
            Return
        End If

        Dim orderId As String = dgvOrders.SelectedRows(0).Cells("colOrderId").Value.ToString()
        Dim status As String = dgvOrders.SelectedRows(0).Cells("colStatus").Value.ToString()

        ' 只有「待確認」和「處理中」的訂單可以取消
        If status <> "待確認" AndAlso status <> "處理中" Then
            MessageBox.Show($"狀態為「{status}」的訂單無法取消", "無法取消", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Dim reason As String = InputBox("請輸入取消原因：", "取消訂單", "")
        If String.IsNullOrEmpty(reason) Then Return

        If _db.CancelOrder(orderId, reason) Then
            MessageBox.Show("訂單已取消", "完成", MessageBoxButtons.OK, MessageBoxIcon.Information)
            LoadOrders()
        Else
            MessageBox.Show("取消失敗，請稍後再試", "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End If
    End Sub

    Private Sub btnPrevPage_Click(sender As Object, e As EventArgs) Handles btnPrevPage.Click
        _currentPage -= 1
        LoadOrders()
    End Sub

    Private Sub btnNextPage_Click(sender As Object, e As EventArgs) Handles btnNextPage.Click
        _currentPage += 1
        LoadOrders()
    End Sub

    Private Sub btnPrint_Click(sender As Object, e As EventArgs) Handles btnPrint.Click
        ' 列印目前篩選條件的訂單明細報表
        MessageBox.Show("列印功能開發中", "提示")
    End Sub
End Class
