import React, { useState, useRef, useEffect } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Tag } from 'primereact/tag';
import { Avatar } from 'primereact/avatar';
import { Menu } from 'primereact/menu';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { Card } from 'primereact/card';
import { Toolbar } from 'primereact/toolbar';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Paginator } from 'primereact/paginator';
import { Skeleton } from 'primereact/skeleton';
import { Badge } from 'primereact/badge';
import { Sidebar } from 'primereact/sidebar';
import { UserService } from '../../services/userService';
import { useAuthStore } from '../../stores/authStore';
import { 
  User, 
  UserRole, 
  UserStatus, 
  UserListParams, 
  ROLE_LABELS, 
  STATUS_LABELS,
  ROLE_HIERARCHY 
} from '../../types/user';
import { UserProfile } from './UserProfile';
import './UserManagement.css';

interface UserManagementProps {
  onUserSelect?: (user: User) => void;
  selectionMode?: 'single' | 'multiple' | 'none';
}

export const UserManagement: React.FC<UserManagementProps> = ({
  onUserSelect,
  selectionMode = 'single'
}) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [selectedUsers, setSelectedUsers] = useState<User[]>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  
  // Pagination state
  const [first, setFirst] = useState(0);
  const [rows, setRows] = useState(10);
  
  // Filter states
  const [roleFilter, setRoleFilter] = useState<UserRole | null>(null);
  const [statusFilter, setStatusFilter] = useState<UserStatus | null>(null);
  
  // Dialog states
  const [showUserDialog, setShowUserDialog] = useState(false);
  const [showProfileSidebar, setShowProfileSidebar] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create');
  
  const toast = useRef<Toast>(null);
  const actionMenu = useRef<Menu>(null);
  const { user: currentUser } = useAuthStore();

  const userService = new UserService();

  // Role and status options for filters
  const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({
    label,
    value: value as UserRole
  }));

  const statusOptions = Object.entries(STATUS_LABELS).map(([value, label]) => ({
    label,
    value: value as UserStatus
  }));

  useEffect(() => {
    loadUsers();
  }, [first, rows, globalFilter, roleFilter, statusFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      
      const params: UserListParams = {
        skip: first,
        limit: rows,
        search: globalFilter || undefined,
        role: roleFilter || undefined,
        status: statusFilter || undefined
      };

      const response = await UserService.getUsers(params);
      
      setUsers(response.users);
      setTotalRecords(response.total);
      
    } catch (error) {
      console.error('Load users error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '載入失敗',
        detail: '無法載入用戶列表',
        life: 5000
      });
    } finally {
      setLoading(false);
    }
  };

  const onPageChange = (event: any) => {
    setFirst(event.first);
    setRows(event.rows);
  };

  const handleUserAction = (action: string, user: User) => {
    setSelectedUser(user);
    
    switch (action) {
      case 'view':
        setShowProfileSidebar(true);
        break;
      case 'edit':
        setDialogMode('edit');
        setShowUserDialog(true);
        break;
      case 'delete':
        confirmDeleteUser(user);
        break;
      case 'activate':
        toggleUserStatus(user, UserStatus.ACTIVE);
        break;
      case 'deactivate':
        toggleUserStatus(user, UserStatus.INACTIVE);
        break;
      case 'suspend':
        toggleUserStatus(user, UserStatus.SUSPENDED);
        break;
      default:
        break;
    }
  };

  const toggleUserStatus = async (user: User, newStatus: UserStatus) => {
    try {
      await UserService.updateUser(user.id, { status: newStatus });
      
      toast.current?.show({
        severity: 'success',
        summary: '狀態已更新',
        detail: `用戶 ${user.username} 的狀態已更新為 ${STATUS_LABELS[newStatus]}`,
        life: 3000
      });
      
      await loadUsers();
    } catch (error) {
      console.error('Update user status error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '更新失敗',
        detail: '無法更新用戶狀態',
        life: 5000
      });
    }
  };

  const confirmDeleteUser = (user: User) => {
    // Implementation would use ConfirmDialog
    // For now, we'll just show a toast
    toast.current?.show({
      severity: 'warn',
      summary: '功能開發中',
      detail: '刪除用戶功能正在開發中',
      life: 3000
    });
  };

  const canManageUser = (user: User): boolean => {
    if (!currentUser) return false;
    
    // Super admin can manage everyone
    if (currentUser.role === UserRole.SUPER_ADMIN) return true;
    
    // Admin can manage users with lower role hierarchy
    if (currentUser.role === UserRole.ADMIN) {
      return ROLE_HIERARCHY[user.role] < ROLE_HIERARCHY[currentUser.role];
    }
    
    // Manager can only manage developers and viewers
    if (currentUser.role === UserRole.MANAGER) {
      return [UserRole.DEVELOPER, UserRole.VIEWER].includes(user.role);
    }
    
    return false;
  };

  // Column templates
  const avatarBodyTemplate = (rowData: User) => {
    return (
      <Avatar
        image={rowData.avatar_url}
        icon={!rowData.avatar_url ? 'pi pi-user' : undefined}
        size="normal"
        shape="circle"
        className="user-avatar"
      />
    );
  };

  const nameBodyTemplate = (rowData: User) => {
    return (
      <div className="user-name-cell">
        <div className="user-full-name">{rowData.full_name || rowData.username}</div>
        <small className="user-username">@{rowData.username}</small>
      </div>
    );
  };

  const roleBodyTemplate = (rowData: User) => {
    const getRoleSeverity = (role: UserRole) => {
      switch (role) {
        case UserRole.SUPER_ADMIN: return 'danger';
        case UserRole.ADMIN: return 'warning';
        case UserRole.MANAGER: return 'info';
        case UserRole.DEVELOPER: return 'success';
        case UserRole.VIEWER: return null;
        default: return null;
      }
    };

    return (
      <Tag
        value={ROLE_LABELS[rowData.role]}
        severity={getRoleSeverity(rowData.role)}
        className="role-tag"
      />
    );
  };

  const statusBodyTemplate = (rowData: User) => {
    const getStatusSeverity = (status: UserStatus) => {
      switch (status) {
        case UserStatus.ACTIVE: return 'success';
        case UserStatus.INACTIVE: return 'secondary';
        case UserStatus.PENDING: return 'warning';
        case UserStatus.SUSPENDED: return 'danger';
        case UserStatus.LOCKED: return 'danger';
        default: return 'secondary';
      }
    };

    return (
      <Tag
        value={STATUS_LABELS[rowData.status]}
        severity={getStatusSeverity(rowData.status)}
        className="status-tag"
      />
    );
  };

  const lastLoginBodyTemplate = (rowData: User) => {
    if (!rowData.last_login_at) {
      return <span className="text-muted">從未登入</span>;
    }
    
    const lastLogin = new Date(rowData.last_login_at);
    const now = new Date();
    const diffMs = now.getTime() - lastLogin.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return <span className="text-success">今天</span>;
    } else if (diffDays === 1) {
      return <span className="text-info">昨天</span>;
    } else if (diffDays <= 7) {
      return <span className="text-warning">{diffDays} 天前</span>;
    } else {
      return <span className="text-muted">{lastLogin.toLocaleDateString()}</span>;
    }
  };

  const actionBodyTemplate = (rowData: User) => {
    const menuItems = [
      {
        label: '查看資料',
        icon: 'pi pi-eye',
        command: () => handleUserAction('view', rowData)
      }
    ];

    if (canManageUser(rowData)) {
      menuItems.push(
        {
          label: '編輯資料',
          icon: 'pi pi-pencil',
          command: () => handleUserAction('edit', rowData)
        },
        { separator: true }
      );

      if (rowData.status === UserStatus.ACTIVE) {
        menuItems.push({
          label: '停用帳號',
          icon: 'pi pi-ban',
          command: () => handleUserAction('deactivate', rowData)
        });
      } else {
        menuItems.push({
          label: '啟用帳號',
          icon: 'pi pi-check',
          command: () => handleUserAction('activate', rowData)
        });
      }

      menuItems.push(
        {
          label: '暫停帳號',
          icon: 'pi pi-pause',
          command: () => handleUserAction('suspend', rowData)
        },
        { separator: true },
        {
          label: '刪除用戶',
          icon: 'pi pi-trash',
          className: 'text-red-500',
          command: () => handleUserAction('delete', rowData)
        }
      );
    }

    return (
      <Button
        icon="pi pi-ellipsis-v"
        className="p-button-rounded p-button-text"
        onClick={(event) => {
          setSelectedUser(rowData);
          actionMenu.current?.toggle(event);
        }}
      />
    );
  };

  const header = (
    <div className="table-header">
      <div className="header-left">
        <h2 className="table-title">
          <i className="pi pi-users mr-2"></i>
          用戶管理
        </h2>
        <Badge value={totalRecords} className="ml-2" />
      </div>
      
      <div className="header-right">
        <div className="filter-controls">
          <span className="p-input-icon-left search-input">
            <i className="pi pi-search" />
            <InputText
              placeholder="搜尋用戶..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
            />
          </span>
          
          <Dropdown
            value={roleFilter}
            options={roleOptions}
            onChange={(e) => setRoleFilter(e.value)}
            placeholder="篩選角色"
            showClear
            className="role-filter"
          />
          
          <Dropdown
            value={statusFilter}
            options={statusOptions}
            onChange={(e) => setStatusFilter(e.value)}
            placeholder="篩選狀態"
            showClear
            className="status-filter"
          />
        </div>
        
        <Button
          label="新增用戶"
          icon="pi pi-plus"
          onClick={() => {
            setDialogMode('create');
            setSelectedUser(null);
            setShowUserDialog(true);
          }}
          className="create-user-btn"
        />
      </div>
    </div>
  );

  if (loading) {
    return (
      <Card className="user-management-card">
        <div className="table-header mb-4">
          <Skeleton width="200px" height="2rem" />
          <Skeleton width="300px" height="2.5rem" />
        </div>
        <DataTable value={Array(5).fill({})} className="p-datatable-loading">
          <Column body={<Skeleton />} header="頭像" />
          <Column body={<Skeleton />} header="姓名" />
          <Column body={<Skeleton />} header="電子郵件" />
          <Column body={<Skeleton />} header="角色" />
          <Column body={<Skeleton />} header="狀態" />
          <Column body={<Skeleton />} header="最後登入" />
          <Column body={<Skeleton />} header="操作" />
        </DataTable>
      </Card>
    );
  }

  return (
    <div className="user-management-container">
      <Toast ref={toast} />
      <ConfirmDialog />
      <Menu ref={actionMenu} model={[]} popup />
      
      <Card className="user-management-card">
        <DataTable
          value={users}
          selection={selectedUsers}
          onSelectionChange={(e) => {
            setSelectedUsers(e.value);
            if (onUserSelect && e.value.length > 0) {
              onUserSelect(e.value[0]);
            }
          }}
          selectionMode={selectionMode !== 'none' ? selectionMode : undefined}
          header={header}
          responsiveLayout="scroll"
          className="user-table"
          emptyMessage="找不到用戶"
          loading={loading}
        >
          {selectionMode !== 'none' && (
            <Column selectionMode={selectionMode} headerStyle={{ width: '3rem' }} />
          )}
          
          <Column
            body={avatarBodyTemplate}
            header="頭像"
            style={{ width: '80px' }}
          />
          
          <Column
            field="username"
            header="姓名"
            body={nameBodyTemplate}
            sortable
            style={{ minWidth: '200px' }}
          />
          
          <Column
            field="email"
            header="電子郵件"
            sortable
            style={{ minWidth: '250px' }}
          />
          
          <Column
            field="role"
            header="角色"
            body={roleBodyTemplate}
            sortable
            style={{ width: '120px' }}
          />
          
          <Column
            field="status"
            header="狀態"
            body={statusBodyTemplate}
            sortable
            style={{ width: '100px' }}
          />
          
          <Column
            field="last_login_at"
            header="最後登入"
            body={lastLoginBodyTemplate}
            sortable
            style={{ width: '120px' }}
          />
          
          <Column
            header="操作"
            body={actionBodyTemplate}
            style={{ width: '80px' }}
          />
        </DataTable>
        
        <Paginator
          first={first}
          rows={rows}
          totalRecords={totalRecords}
          onPageChange={onPageChange}
          rowsPerPageOptions={[5, 10, 20, 50]}
          template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          currentPageReportTemplate="顯示 {first} 到 {last} 筆，共 {totalRecords} 筆"
          className="mt-4"
        />
      </Card>

      {/* User Profile Sidebar */}
      <Sidebar
        visible={showProfileSidebar}
        position="right"
        onHide={() => setShowProfileSidebar(false)}
        className="user-profile-sidebar"
        style={{ width: '60vw', minWidth: '600px' }}
      >
        {selectedUser && (
          <UserProfile
            userId={selectedUser.id.toString()}
            viewMode={!canManageUser(selectedUser)}
          />
        )}
      </Sidebar>

      {/* User Create/Edit Dialog */}
      <Dialog
        visible={showUserDialog}
        style={{ width: '50vw', minWidth: '500px' }}
        header={dialogMode === 'create' ? '新增用戶' : '編輯用戶'}
        modal
        onHide={() => setShowUserDialog(false)}
        draggable={false}
        resizable={false}
      >
        <div className="p-4">
          {/* TODO: Implement UserForm component */}
          <p className="text-center text-muted">
            用戶表單組件開發中...
          </p>
        </div>
      </Dialog>
    </div>
  );
};

export default UserManagement;
