''' <summary>
''' 訂單金額計算模組
''' 包含折扣、稅金、運費等計算邏輯
''' </summary>
Public Class OrderCalculator

    ' 稅率設定（依法規為 5%）
    Private Const TAX_RATE As Decimal = 0.05D

    ' 免運費門檻
    Private Const FREE_SHIPPING_THRESHOLD As Decimal = 3000D

    ' 基本運費
    Private Const BASE_SHIPPING_FEE As Decimal = 150D

    ''' <summary>
    ''' 計算明細行小計（考量折扣）
    ''' </summary>
    Public Function CalcLineTotal(quantity As Integer, unitPrice As Decimal, discountPercent As Decimal) As Decimal
        Return quantity * unitPrice * (1 - discountPercent / 100D)
    End Function

    ''' <summary>
    ''' 計算訂單總金額（含稅、含運費）
    ''' 計算順序：1) 計算各行小計 → 2) 加總 → 3) 套用整單折扣 → 4) 計算稅金 → 5) 加運費
    ''' </summary>
    Public Function CalcOrderTotal(lines As IEnumerable(Of OrderLine), orderDiscount As Decimal, includeShipping As Boolean) As OrderTotals
        Dim result As New OrderTotals()

        ' 1. 各行小計加總（已含明細折扣）
        result.SubTotal = lines.Sum(Function(l) CalcLineTotal(l.Quantity, l.UnitPrice, l.DiscountPercent))

        ' 2. 套用整單折扣
        result.OrderDiscountAmount = result.SubTotal * orderDiscount / 100D
        result.AfterDiscount = result.SubTotal - result.OrderDiscountAmount

        ' 3. 計算稅金（稅前金額 × 5%，無條件捨去至元）
        result.TaxAmount = Math.Floor(result.AfterDiscount * TAX_RATE)

        ' 4. 計算運費（含稅後金額未達門檻則加收運費）
        If includeShipping Then
            result.ShippingFee = If(result.AfterDiscount + result.TaxAmount >= FREE_SHIPPING_THRESHOLD, 0D, BASE_SHIPPING_FEE)
        End If

        ' 5. 最終總計
        result.GrandTotal = result.AfterDiscount + result.TaxAmount + result.ShippingFee

        Return result
    End Function

    ''' <summary>
    ''' 判斷客戶是否符合 VIP 優惠資格
    ''' 條件：近 12 個月累計訂單金額超過 NT$100,000，且信用等級為 A 或 B
    ''' </summary>
    Public Function IsVipEligible(annualPurchaseAmount As Decimal, creditGrade As String) As Boolean
        Return annualPurchaseAmount >= 100000D AndAlso
               (creditGrade = "A" OrElse creditGrade = "B")
    End Function

    ''' <summary>
    ''' 計算 VIP 客戶優惠折扣率
    ''' 規則：100萬以上 8折、50萬以上 85折、20萬以上 9折、10萬以上 95折
    ''' </summary>
    Public Function GetVipDiscountRate(annualPurchaseAmount As Decimal) As Decimal
        Select Case True
            Case annualPurchaseAmount >= 1000000D : Return 20D  ' 八折
            Case annualPurchaseAmount >= 500000D  : Return 15D  ' 八五折
            Case annualPurchaseAmount >= 200000D  : Return 10D  ' 九折
            Case Else                             : Return 5D   ' 九五折
        End Select
    End Function
End Class

' 訂單行資料結構
Public Class OrderLine
    Public Property ProductID As String
    Public Property Quantity As Integer
    Public Property UnitPrice As Decimal
    Public Property DiscountPercent As Decimal
End Class

' 訂單金額明細
Public Class OrderTotals
    Public Property SubTotal As Decimal        ' 明細小計合計
    Public Property OrderDiscountAmount As Decimal  ' 整單折扣金額
    Public Property AfterDiscount As Decimal   ' 折扣後金額
    Public Property TaxAmount As Decimal       ' 稅金（5%）
    Public Property ShippingFee As Decimal     ' 運費
    Public Property GrandTotal As Decimal      ' 最終總計
End Class
