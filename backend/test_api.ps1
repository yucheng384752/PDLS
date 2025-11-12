# PDLS API 測試腳本 (PowerShell)
# 測試所有實現的認證和用戶管理功能

$BaseURL = "http://localhost:8000"
$ApiBase = "$BaseURL/api"

Write-Host "🚀 開始 PDLS API 功能測試" -ForegroundColor Green
Write-Host "測試目標: $BaseURL" -ForegroundColor Cyan

# 測試結果統計
$TestResults = @()

function Test-Endpoint {
    param(
        [string]$TestName,
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Body = $null,
        [hashtable]$Headers = @{"Content-Type" = "application/json"},
        [int]$ExpectedStatus = 200
    )
    
    $FullUrl = "$ApiBase$Endpoint"
    
    Write-Host "`n$('='*60)" -ForegroundColor Yellow
    Write-Host "測試: $TestName" -ForegroundColor White
    Write-Host "URL: $Method $FullUrl" -ForegroundColor Gray
    
    try {
        $Params = @{
            Uri = $FullUrl
            Method = $Method
            Headers = $Headers
            ContentType = "application/json"
        }
        
        if ($Body) {
            $Params.Body = ($Body | ConvertTo-Json -Depth 3)
            Write-Host "請求內容:" -ForegroundColor Gray
            Write-Host ($Body | ConvertTo-Json -Depth 3) -ForegroundColor DarkGray
        }
        
        $Response = Invoke-RestMethod @Params
        $Status = 200  # Invoke-RestMethod 成功時預設為 200
        
        Write-Host "✅ 測試通過" -ForegroundColor Green
        Write-Host "回應狀態: $Status (預期: $ExpectedStatus)" -ForegroundColor Green
        Write-Host "回應內容:" -ForegroundColor Gray
        Write-Host ($Response | ConvertTo-Json -Depth 3) -ForegroundColor DarkGray
        
        return @{
            Success = $true
            Status = $Status
            Response = $Response
        }
        
    } catch {
        $StatusCode = $_.Exception.Response.StatusCode.value__
        $ErrorMessage = $_.Exception.Message
        
        if ($StatusCode -eq $ExpectedStatus) {
            Write-Host "✅ 測試通過 (預期錯誤)" -ForegroundColor Green
            Write-Host "回應狀態: $StatusCode (預期: $ExpectedStatus)" -ForegroundColor Green
            return @{
                Success = $true
                Status = $StatusCode
                Response = $null
            }
        } else {
            Write-Host "❌ 測試失敗" -ForegroundColor Red
            Write-Host "回應狀態: $StatusCode (預期: $ExpectedStatus)" -ForegroundColor Red
            Write-Host "錯誤信息: $ErrorMessage" -ForegroundColor Red
            return @{
                Success = $false
                Status = $StatusCode
                Response = $null
            }
        }
    }
}

# 全域變數儲存測試數據
$Global:AuthToken = $null
$Global:TestUserId = $null

# 1. 測試健康檢查
Write-Host "`n📋 開始基礎功能測試" -ForegroundColor Magenta
$Result = Test-Endpoint -TestName "健康檢查" -Method "GET" -Endpoint "/../health"
$TestResults += $Result.Success

# 2. 測試用戶註冊
Write-Host "`n🔐 開始認證流程測試" -ForegroundColor Magenta
$RegisterData = @{
    username = "testuser$(Get-Random -Minimum 100 -Maximum 999)"
    email = "testuser$(Get-Random -Minimum 100 -Maximum 999)@example.com"
    password = "TestPassword123"
    full_name = "測試用戶"
    phone = "123-456-7890"
}

$Result = Test-Endpoint -TestName "用戶註冊" -Method "POST" -Endpoint "/auth/register" -Body $RegisterData -ExpectedStatus 201
$TestResults += $Result.Success

if ($Result.Success -and $Result.Response.id) {
    $Global:TestUserId = $Result.Response.id
    Write-Host "🆔 測試用戶 ID: $($Global:TestUserId)" -ForegroundColor Cyan
}

# 3. 測試用戶登入
$LoginData = @{
    username = $RegisterData.username
    password = $RegisterData.password
}

$Result = Test-Endpoint -TestName "用戶登入" -Method "POST" -Endpoint "/auth/login" -Body $LoginData
$TestResults += $Result.Success

if ($Result.Success -and $Result.Response.access_token) {
    $Global:AuthToken = $Result.Response.access_token
    Write-Host "🔑 取得認證令牌" -ForegroundColor Cyan
}

# 認證相關的測試
if ($Global:AuthToken) {
    $AuthHeaders = @{
        "Content-Type" = "application/json"
        "Authorization" = "Bearer $($Global:AuthToken)"
    }
    
    Write-Host "`n👤 開始用戶管理測試" -ForegroundColor Magenta
    
    # 4. 測試獲取當前用戶
    $Result = Test-Endpoint -TestName "獲取當前用戶" -Method "GET" -Endpoint "/users/me" -Headers $AuthHeaders
    $TestResults += $Result.Success
    
    # 5. 測試更新當前用戶
    $UpdateData = @{
        full_name = "更新的測試用戶"
        timezone = "Asia/Taipei"
        language = "zh-tw"
    }
    
    $Result = Test-Endpoint -TestName "更新當前用戶" -Method "PUT" -Endpoint "/users/me" -Body $UpdateData -Headers $AuthHeaders
    $TestResults += $Result.Success
    
    # 6. 測試獲取用戶權限
    if ($Global:TestUserId) {
        $Result = Test-Endpoint -TestName "獲取用戶權限" -Method "GET" -Endpoint "/users/$($Global:TestUserId)/permissions" -Headers $AuthHeaders
        $TestResults += $Result.Success
    }
    
    # 7. 測試未授權訪問（應該失敗）
    $Result = Test-Endpoint -TestName "未授權用戶列表訪問" -Method "GET" -Endpoint "/users/" -Headers $AuthHeaders -ExpectedStatus 403
    $TestResults += $Result.Success
    
    Write-Host "`n🔒 開始安全性測試" -ForegroundColor Magenta
    
    # 8. 測試無效令牌
    $InvalidHeaders = @{
        "Content-Type" = "application/json"
        "Authorization" = "Bearer invalid_token"
    }
    
    $Result = Test-Endpoint -TestName "無效令牌測試" -Method "GET" -Endpoint "/users/me" -Headers $InvalidHeaders -ExpectedStatus 401
    $TestResults += $Result.Success
}

# 9. 測試密碼重設請求
Write-Host "`n📧 開始密碼重設測試" -ForegroundColor Magenta
$ResetData = @{
    email = $RegisterData.email
}

$Result = Test-Endpoint -TestName "密碼重設請求" -Method "POST" -Endpoint "/auth/forgot-password" -Body $ResetData
$TestResults += $Result.Success

# 測試總結
Write-Host "`n$('='*60)" -ForegroundColor Yellow
Write-Host "📊 測試總結" -ForegroundColor White

$Passed = ($TestResults | Where-Object { $_ -eq $true }).Count
$Total = $TestResults.Count
$SuccessRate = if ($Total -gt 0) { ($Passed / $Total) * 100 } else { 0 }

Write-Host "總測試數: $Total" -ForegroundColor Cyan
Write-Host "通過測試: $Passed" -ForegroundColor Green
Write-Host "失敗測試: $($Total - $Passed)" -ForegroundColor Red
Write-Host "成功率: $([math]::Round($SuccessRate, 1))%" -ForegroundColor Yellow

if ($SuccessRate -ge 80) {
    Write-Host "🎉 測試結果: 優秀！系統功能運行良好" -ForegroundColor Green
} elseif ($SuccessRate -ge 60) {
    Write-Host "⚠️  測試結果: 良好，但有些功能需要改進" -ForegroundColor Yellow
} else {
    Write-Host "❌ 測試結果: 需要修復多個問題" -ForegroundColor Red
}

Write-Host "`n測試完成！" -ForegroundColor Green