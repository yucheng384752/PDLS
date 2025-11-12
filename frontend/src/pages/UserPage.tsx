import React, { useState } from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { UserProfile } from '../components/user/UserProfile';
import { UserManagement } from '../components/user/UserManagement';
import { useAuthStore } from '../stores/authStore';
import { UserRole } from '../types/user';
import './UserPage.css';

export const UserPage: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const { user } = useAuthStore();

  // Check if user has management permissions
  const canManageUsers = user?.role && [
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.MANAGER
  ].includes(user.role);

  return (
    <div className="user-page-container">
      <Card className="user-page-card">
        <div className="user-page-header">
          <h2>用戶管理系統</h2>
          <p className="text-muted">
            管理個人資料、查看用戶列表和系統權限
          </p>
        </div>

        <TabView
          activeIndex={activeIndex}
          onTabChange={(e) => setActiveIndex(e.index)}
          className="user-tabs"
        >
          {/* Personal Profile Tab */}
          <TabPanel header="個人資料" leftIcon="pi pi-user">
            <div className="tab-content">
              <UserProfile />
            </div>
          </TabPanel>

          {/* User Management Tab - Only for authorized roles */}
          {canManageUsers && (
            <TabPanel header="用戶管理" leftIcon="pi pi-users">
              <div className="tab-content">
                <UserManagement />
              </div>
            </TabPanel>
          )}

          {/* User Directory Tab - Read-only view for all users */}
          <TabPanel header="用戶目錄" leftIcon="pi pi-book">
            <div className="tab-content">
              <UserManagement readonly={true} />
            </div>
          </TabPanel>
        </TabView>
      </Card>
    </div>
  );
};

export default UserPage;