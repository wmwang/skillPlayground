VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "clsInventory"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False

' ====================================================
' 庫存計算邏輯類別
' 包含進貨成本計算、庫存週轉率等業務邏輯
' ====================================================

' 計算加權平均成本（當新進貨時重新計算庫存成本）
' 公式：(現有庫存 × 現有成本 + 新進數量 × 進貨成本) / (現有庫存 + 新進數量)
Public Function CalcWeightedAvgCost(currentQty As Integer, currentCost As Double, _
                                     newQty As Integer, newCost As Double) As Double
    If currentQty + newQty = 0 Then
        CalcWeightedAvgCost = 0
        Exit Function
    End If

    CalcWeightedAvgCost = (currentQty * currentCost + newQty * newCost) / (currentQty + newQty)
End Function

' 計算庫存週轉率（年化）
' 公式：年銷售成本 / 平均庫存成本
' 週轉率越高代表庫存管理越有效率
Public Function CalcInventoryTurnover(annualCOGS As Double, avgInventoryValue As Double) As Double
    If avgInventoryValue = 0 Then
        CalcInventoryTurnover = 0
        Exit Function
    End If
    CalcInventoryTurnover = annualCOGS / avgInventoryValue
End Function

' 計算安全庫存量（考量前置時間與需求波動）
' 公式：Z × 標準差 × sqrt(前置時間天數)
' Z 值：1.65 (95% 服務水準)
Public Function CalcSafetyStock(demandStdDev As Double, leadTimeDays As Integer) As Integer
    Const Z_95 As Double = 1.65   ' 95% 服務水準
    CalcSafetyStock = CInt(Z_95 * demandStdDev * Sqr(leadTimeDays))
End Function

' 計算建議補貨點 (Reorder Point)
' 公式：平均日需求 × 前置時間 + 安全庫存
Public Function CalcReorderPoint(avgDailyDemand As Double, leadTimeDays As Integer, safetyStock As Integer) As Integer
    CalcReorderPoint = CInt(avgDailyDemand * leadTimeDays) + safetyStock
End Function

' 計算建議訂購量（EOQ，經濟訂購量）
' 公式：sqrt(2 × 年需求量 × 訂購成本 / 持有成本率 / 單位成本)
Public Function CalcEOQ(annualDemand As Double, orderCost As Double, _
                         holdingRate As Double, unitCost As Double) As Integer
    If holdingRate = 0 Or unitCost = 0 Then
        CalcEOQ = 0
        Exit Function
    End If
    CalcEOQ = CInt(Sqr(2 * annualDemand * orderCost / (holdingRate * unitCost)))
End Function
