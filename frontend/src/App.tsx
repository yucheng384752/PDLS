import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { PrimeReactProvider } from 'primereact/api';
import LoginForm from './components/user/LoginForm';
import RegisterForm from './components/user/RegisterForm';
import { UserManagementPage } from './pages/UserManagementPage';
import ProjectCreatePage from './pages/ProjectCreatePage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import { useAuthStore } from './stores/authStore';
import 'primereact/resources/themes/saga-blue/theme.css';
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import './App.css';

// Protected Route Component
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore();
  
  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">
          <i className="pi pi-spin pi-spinner" style={{ fontSize: '2rem' }}></i>
          <p>載入中...</p>
        </div>
      </div>
    );
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

// Public Route Component (redirect if authenticated)
interface PublicRouteProps {
  children: React.ReactNode;
}

const PublicRoute: React.FC<PublicRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore();
  
  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">
          <i className="pi pi-spin pi-spinner" style={{ fontSize: '2rem' }}></i>
          <p>載入中...</p>
        </div>
      </div>
    );
  }
  
  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" replace />;
};

// Main App Layout
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuthStore();

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1 className="app-title">
              <i className="pi pi-book mr-2"></i>
              PDLS
            </h1>
            <span className="app-subtitle">專案開發日誌系統</span>
          </div>
          
          {user && (
            <div className="header-right">
              <div className="user-info">
                <span className="user-name">{user.full_name || user.username}</span>
                <span className="user-role">{user.role}</span>
              </div>
              <button 
                className="logout-btn"
                onClick={logout}
                title="登出"
              >
                <i className="pi pi-sign-out"></i>
              </button>
            </div>
          )}
        </div>
      </header>
      
      <main className="app-main">
        {children}
      </main>
      
      <footer className="app-footer">
        <div className="footer-content">
          <p>&copy; 2024 PDLS - 專案開發日誌系統</p>
        </div>
      </footer>
    </div>
  );
};

// Dashboard component (temporary)
const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  
  return (
    <div className="dashboard">
      <div className="welcome-section">
        <h2>歡迎回來，{user?.full_name || user?.username}！</h2>
        <p className="welcome-subtitle">
          這是您的專案開發日誌管理中心
        </p>
      </div>
      
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <div className="card-icon">
            <i className="pi pi-users"></i>
          </div>
          <div className="card-content">
            <h3>用戶管理</h3>
            <p>管理系統用戶和權限</p>
            <a href="/users" className="card-link">
              前往管理 <i className="pi pi-arrow-right"></i>
            </a>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">
            <i className="pi pi-folder"></i>
          </div>
          <div className="card-content">
            <h3>專案管理</h3>
            <p>建立和管理開發專案</p>
            <a href="/projects/create" className="card-link">
              建立專案 <i className="pi pi-arrow-right"></i>
            </a>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">
            <i className="pi pi-calendar"></i>
          </div>
          <div className="card-content">
            <h3>工時紀錄</h3>
            <p>記錄和追蹤工作時間</p>
            <span className="card-link disabled">
              開發中 <i className="pi pi-clock"></i>
            </span>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">
            <i className="pi pi-chart-bar"></i>
          </div>
          <div className="card-content">
            <h3>報表統計</h3>
            <p>查看專案進度和統計</p>
            <span className="card-link disabled">
              開發中 <i className="pi pi-clock"></i>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  return (
    <PrimeReactProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={
              <PublicRoute>
                <LoginForm />
              </PublicRoute>
            } />
            
            <Route path="/register" element={
              <PublicRoute>
                <RegisterForm />
              </PublicRoute>
            } />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <AppLayout>
                  <Dashboard />
                </AppLayout>
              </ProtectedRoute>
            } />
            
            <Route path="/users" element={
              <ProtectedRoute>
                <AppLayout>
                  <UserManagementPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            
            <Route path="/projects/create" element={
              <ProtectedRoute>
                <AppLayout>
                  <ProjectCreatePage />
                </AppLayout>
              </ProtectedRoute>
            } />
            
            <Route path="/projects/:projectId" element={
              <ProtectedRoute>
                <AppLayout>
                  <ProjectDetailPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            
            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* 404 Route */}
            <Route path="*" element={
              <AppLayout>
                <div className="not-found">
                  <h2>404 - 頁面不存在</h2>
                  <p>您要找的頁面不存在</p>
                  <a href="/dashboard">返回首頁</a>
                </div>
              </AppLayout>
            } />
          </Routes>
        </div>
      </Router>
    </PrimeReactProvider>
  );
};

export default App;