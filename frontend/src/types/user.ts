/**
 * User-related type definitions for PDLS frontend
 */

// Enums
export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  MANAGER = 'manager',
  DEVELOPER = 'developer',
  VIEWER = 'viewer'
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  SUSPENDED = 'suspended',
  LOCKED = 'locked'
}

// Base user interface
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  phone?: string;
  role: UserRole;
  status: UserStatus;
  timezone: string;
  language: string;
  email_verified: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at?: string;
}

// Authentication related types
export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  timezone?: string;
  language?: string;
}

// Extended user profile interface with additional fields
export interface UserProfile extends User {
  avatar_url?: string;
  bio?: string;
  birth_date?: string;
  receive_notifications: boolean;
  is_public_profile: boolean;
}

// Update user profile request
export interface UpdateUserProfile {
  username: string;
  email: string;
  full_name: string;
  phone?: string;
  timezone: string;
  language: string;
  bio?: string;
  birth_date?: Date | null;
  receive_notifications: boolean;
  is_public_profile: boolean;
}

// Change password request
export interface ChangePassword {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

// User management types
export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  role: UserRole;
  timezone?: string;
  language?: string;
}

export interface UserUpdateRequest {
  full_name?: string;
  phone?: string;
  timezone?: string;
  language?: string;
  status?: UserStatus;
}

export interface UserRoleUpdateRequest {
  role: UserRole;
}

export interface UserListParams {
  skip?: number;
  limit?: number;
  role?: UserRole;
  status?: UserStatus;
  search?: string;
}

export interface UserListResponse {
  users: User[];
  total: number;
  skip: number;
  limit: number;
}

export interface UserPermissions {
  user_id: number;
  username: string;
  role: UserRole;
  permissions: string[];
}

// UI related types
export interface FormErrors {
  [key: string]: string | undefined;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface UserManagementState {
  users: User[];
  currentUser: User | null;
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  filters: {
    search: string;
    role: UserRole | null;
    status: UserStatus | null;
  };
}

// Form validation schemas
export interface LoginFormData {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  fullName?: string;
  phone?: string;
  timezone?: string;
  language?: string;
  acceptTerms: boolean;
}

export interface ProfileFormData {
  fullName?: string;
  phone?: string;
  timezone?: string;
  language?: string;
}

export interface PasswordChangeFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface UserCreateFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  fullName?: string;
  phone?: string;
  role: UserRole;
  timezone?: string;
  language?: string;
}

// Utility types
export type UserRoleLevel = {
  [K in UserRole]: number;
};

export interface RolePermissionMap {
  [key: string]: string[];
}

// Constants for role hierarchy
export const ROLE_HIERARCHY: UserRoleLevel = {
  [UserRole.VIEWER]: 0,
  [UserRole.DEVELOPER]: 1,
  [UserRole.MANAGER]: 2,
  [UserRole.ADMIN]: 3,
  [UserRole.SUPER_ADMIN]: 4,
};

// Role labels for display
export const ROLE_LABELS: Record<UserRole, string> = {
  [UserRole.SUPER_ADMIN]: '超級管理員',
  [UserRole.ADMIN]: '管理員',
  [UserRole.MANAGER]: '專案經理',
  [UserRole.DEVELOPER]: '開發者',
  [UserRole.VIEWER]: '觀察者',
};

// Status labels for display
export const STATUS_LABELS: Record<UserStatus, string> = {
  [UserStatus.ACTIVE]: '啟用',
  [UserStatus.INACTIVE]: '停用',
  [UserStatus.PENDING]: '待審核',
  [UserStatus.SUSPENDED]: '暫停',
  [UserStatus.LOCKED]: '鎖定',
};

// Timezone options
export const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'Asia/Taipei', label: 'Asia/Taipei (台北時間)' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai (中國標準時間)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (日本標準時間)' },
  { value: 'America/New_York', label: 'America/New_York (Eastern Time)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (Pacific Time)' },
  { value: 'Europe/London', label: 'Europe/London (GMT)' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin (CET)' },
];

// Language options
export const LANGUAGE_OPTIONS = [
  { value: 'zh-tw', label: '繁體中文' },
  { value: 'zh-cn', label: '简体中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
];

// Permission definitions
export const PERMISSIONS = {
  // User management
  VIEW_USERS: 'view_users',
  CREATE_USERS: 'create_users',
  UPDATE_USERS: 'update_users',
  DELETE_USERS: 'delete_users',
  MANAGE_USER_ROLES: 'manage_user_roles',
  
  // Project management
  VIEW_PROJECTS: 'view_projects',
  CREATE_PROJECTS: 'create_projects',
  UPDATE_PROJECTS: 'update_projects',
  DELETE_PROJECTS: 'delete_projects',
  MANAGE_PROJECT_MEMBERS: 'manage_project_members',
  
  // Development logs
  VIEW_LOGS: 'view_logs',
  CREATE_LOGS: 'create_logs',
  UPDATE_OWN_LOGS: 'update_own_logs',
  UPDATE_ALL_LOGS: 'update_all_logs',
  DELETE_OWN_LOGS: 'delete_own_logs',
  DELETE_ALL_LOGS: 'delete_all_logs',
  
  // System administration
  VIEW_SYSTEM_CONFIG: 'view_system_config',
  UPDATE_SYSTEM_CONFIG: 'update_system_config',
  VIEW_AUDIT_LOGS: 'view_audit_logs',
  MANAGE_BACKUPS: 'manage_backups',
} as const;

export type Permission = typeof PERMISSIONS[keyof typeof PERMISSIONS];