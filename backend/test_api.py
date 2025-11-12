"""
PDLS API 功能測試腳本
測試所有實現的認證和用戶管理功能
"""

import asyncio
import aiohttp
import json
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

class PDLSAPITester:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.test_user_id: Optional[int] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, auth: bool = False):
        """發送HTTP請求"""
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with self.session.request(
                method, 
                url, 
                json=data,
                headers=headers
            ) as response:
                result = {
                    "status": response.status,
                    "data": await response.json() if response.content_type == "application/json" else await response.text()
                }
                return result
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def print_test_result(self, test_name: str, expected_status: int, result: Dict):
        """打印測試結果"""
        status = result.get("status", "error")
        success = status == expected_status
        
        print(f"\n{'='*60}")
        print(f"測試: {test_name}")
        print(f"預期狀態: {expected_status}, 實際狀態: {status}")
        print(f"結果: {'✅ 通過' if success else '❌ 失敗'}")
        
        if not success or "error" in result:
            print(f"錯誤信息: {result}")
        else:
            print(f"回應數據: {json.dumps(result.get('data', {}), indent=2, ensure_ascii=False)}")
        
        return success
    
    async def test_health_check(self):
        """測試健康檢查端點"""
        result = await self.make_request("GET", "/../health")
        return self.print_test_result("健康檢查", 200, result)
    
    async def test_user_registration(self):
        """測試用戶註冊"""
        test_data = {
            "username": "testuser123",
            "email": "testuser@example.com",
            "password": "TestPassword123",
            "full_name": "測試用戶",
            "phone": "123-456-7890"
        }
        
        result = await self.make_request("POST", "/auth/register", test_data)
        success = self.print_test_result("用戶註冊", 201, result)
        
        if success and result.get("data", {}).get("id"):
            self.test_user_id = result["data"]["id"]
        
        return success
    
    async def test_user_login(self):
        """測試用戶登入"""
        test_data = {
            "username": "testuser123",
            "password": "TestPassword123"
        }
        
        result = await self.make_request("POST", "/auth/login", test_data)
        success = self.print_test_result("用戶登入", 200, result)
        
        if success and result.get("data", {}).get("access_token"):
            self.auth_token = result["data"]["access_token"]
        
        return success
    
    async def test_get_current_user(self):
        """測試獲取當前用戶資料"""
        result = await self.make_request("GET", "/users/me", auth=True)
        return self.print_test_result("獲取當前用戶", 200, result)
    
    async def test_update_current_user(self):
        """測試更新當前用戶資料"""
        test_data = {
            "full_name": "更新的測試用戶",
            "timezone": "Asia/Taipei",
            "language": "zh-tw"
        }
        
        result = await self.make_request("PUT", "/users/me", test_data, auth=True)
        return self.print_test_result("更新當前用戶", 200, result)
    
    async def test_list_users_unauthorized(self):
        """測試未授權訪問用戶列表（應該失敗）"""
        result = await self.make_request("GET", "/users/", auth=True)
        # 普通用戶應該得到403，因為需要Manager+權限
        return self.print_test_result("未授權用戶列表訪問", 403, result)
    
    async def test_password_reset_request(self):
        """測試密碼重設請求"""
        test_data = {
            "email": "testuser@example.com"
        }
        
        result = await self.make_request("POST", "/auth/forgot-password", test_data)
        return self.print_test_result("密碼重設請求", 200, result)
    
    async def test_user_permissions(self):
        """測試獲取用戶權限"""
        if self.test_user_id:
            result = await self.make_request("GET", f"/users/{self.test_user_id}/permissions", auth=True)
            return self.print_test_result("獲取用戶權限", 200, result)
        return False
    
    async def test_invalid_token(self):
        """測試無效令牌"""
        old_token = self.auth_token
        self.auth_token = "invalid_token"
        
        result = await self.make_request("GET", "/users/me", auth=True)
        success = self.print_test_result("無效令牌測試", 401, result)
        
        # 恢復正確的令牌
        self.auth_token = old_token
        return success
    
    async def run_all_tests(self):
        """執行所有測試"""
        print("🚀 開始 PDLS API 功能測試")
        print(f"測試目標: {BASE_URL}")
        
        test_results = []
        
        # 基礎功能測試
        test_results.append(await self.test_health_check())
        
        # 認證流程測試
        test_results.append(await self.test_user_registration())
        test_results.append(await self.test_user_login())
        
        # 用戶管理測試（需要認證）
        if self.auth_token:
            test_results.append(await self.test_get_current_user())
            test_results.append(await self.test_update_current_user())
            test_results.append(await self.test_user_permissions())
            test_results.append(await self.test_list_users_unauthorized())
            test_results.append(await self.test_password_reset_request())
            test_results.append(await self.test_invalid_token())
        
        # 測試總結
        print(f"\n{'='*60}")
        print("📊 測試總結")
        passed = sum(test_results)
        total = len(test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"總測試數: {total}")
        print(f"通過測試: {passed}")
        print(f"失敗測試: {total - passed}")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 測試結果: 優秀！系統功能運行良好")
        elif success_rate >= 60:
            print("⚠️  測試結果: 良好，但有些功能需要改進")
        else:
            print("❌ 測試結果: 需要修復多個問題")
        
        return success_rate >= 80

async def main():
    """主函數"""
    async with PDLSAPITester() as tester:
        success = await tester.run_all_tests()
        return success

if __name__ == "__main__":
    print("PDLS API 自動化測試腳本")
    print("請確保伺服器在 http://localhost:8000 運行")
    input("按 Enter 開始測試...")
    
    try:
        result = asyncio.run(main())
        exit_code = 0 if result else 1
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n測試被用戶中斷")
        exit(1)
    except Exception as e:
        print(f"\n測試過程中發生錯誤: {e}")
        exit(1)