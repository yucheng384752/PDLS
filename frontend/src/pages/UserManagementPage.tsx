import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { UserManagement } from '../components/user/UserManagement';
import { UserProfile } from '../components/user/UserProfile';
import { useAuthStore } from '../stores/authStore';
import { UserRole } from '../types/user';
import './UserManagementPage.css';

export const UserManagementPage: React.FC = () => {
  const { user } = useAuthStore();

  // Check if user has permission to access user management
  const canManageUsers = user && [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.MANAGER
  ].includes(user.role);

  if (!canManageUsers) {
    return (
      <div className="user-management-page">
        <Card className="access-denied-card">
          <div className="access-denied-content">
            <i className="pi pi-lock text-6xl text-gray-400 mb-3"></i>
            <h2>存取被拒絕</h2>
            <p className="text-gray-600 mb-4">
              您沒有權限存取用戶管理功能。
            </p>
            <p className="text-sm text-gray-500">
              如需協助，請聯繫系統管理員。
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="user-management-page">
      <div className="page-header mb-4">
        <h1 className="page-title">
          <i className="pi pi-users mr-3"></i>
          用戶管理中心
        </h1>
        <p className="page-subtitle">
          管理系統用戶、角色和權限
        </p>
      </div>

      <TabView className="user-management-tabs">
        <TabPanel 
          header="用戶列表" 
          leftIcon="pi pi-list mr-2"
        >
          <UserManagement />
        </TabPanel>

        <TabPanel 
          header="個人資料" 
          leftIcon="pi pi-user mr-2"
        >
          <div className="profile-tab-content">
            <Card>
              <h3 className="mb-3">我的個人資料</h3>
              <UserProfile />
            </Card>
          </div>
        </TabPanel>

        {user?.role === UserRole.SUPER_ADMIN && (
          <TabPanel 
            header="系統設定" 
            leftIcon="pi pi-cog mr-2"
          >
            <Card>
              <div className="system-settings-content">
                <h3 className="mb-3">系統設定</h3>
                <p className="text-muted mb-4">
                  系統設定功能開發中...
                </p>
                
                <div className="settings-grid">
                  <div className="setting-item">
                    <i className="pi pi-shield setting-icon"></i>
                    <div className="setting-info">
                      <h5>安全設定</h5>
                      <p>密碼策略、登入限制等安全相關設定</p>
                    </div>
                  </div>

                  <div className="setting-item">
                    <i className="pi pi-envelope setting-icon"></i>
                    <div className="setting-info">
                      <h5>郵件設定</h5>
                      <p>SMTP 伺服器、郵件模板等設定</p>
                    </div>
                  </div>

                  <div className="setting-item">
                    <i className="pi pi-database setting-icon"></i>
                    <div className="setting-info">
                      <h5>備份設定</h5>
                      <p>自動備份、資料保留期限等設定</p>
                    </div>
                  </div>

                  <div className="setting-item">
                    <i className="pi pi-chart-line setting-icon"></i>
                    <div className="setting-info">
                      <h5>監控設定</h5>
                      <p>系統監控、效能追蹤等設定</p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabPanel>
        )}
      </TabView>
    </div>
  );
};

export default UserManagementPage;