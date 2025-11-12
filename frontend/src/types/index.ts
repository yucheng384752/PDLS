/**
 * Base TypeScript types and interfaces for PDLS frontend
 * Provides type safety for all data structures used across the application
 */

// ============= Utility Types =============

export type ID = number;
export type UUID = string;
export type Timestamp = string; // ISO 8601 format
export type FileSize = number; // bytes
export type Email = string;
export type URL = string;

// Generic types for nullable and optional values
export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Maybe<T> = T | null | undefined;

// ============= Enums =============

export enum ResponseStatus {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  PARTIAL = 'partial',
}

export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  DEVELOPER = 'developer',
  VIEWER = 'viewer',
}

export enum ProjectStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  ARCHIVED = 'archived',
}

export enum LogCategory {
  FEATURE = 'feature',
  BUG_FIX = 'bug_fix',
  REFACTOR = 'refactor',
  DOCUMENTATION = 'documentation',
  TESTING = 'testing',
  DEPLOYMENT = 'deployment',
  MEETING = 'meeting',
  RESEARCH = 'research',
  OTHER = 'other',
}

export enum LogPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum FileType {
  IMAGE = 'image',
  DOCUMENT = 'document',
  SPREADSHEET = 'spreadsheet',
  PRESENTATION = 'presentation',
  ARCHIVE = 'archive',
  CODE = 'code',
  OTHER = 'other',
}

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

// ============= Base Entity Interfaces =============

export interface BaseEntity {
  id: ID;
  created_at: Timestamp;
  updated_at: Timestamp;
  deleted_at?: Nullable<Timestamp>;
  is_deleted: boolean;
}

export interface NamedEntity extends BaseEntity {
  name: string;
  description?: Nullable<string>;
}

export interface OwnedEntity extends BaseEntity {
  owner_id: ID;
  created_by_id?: Nullable<ID>;
  updated_by_id?: Nullable<ID>;
}

export interface MetadataEntity extends BaseEntity {
  metadata?: Record<string, any>;
}

// ============= User Types =============

export interface User extends BaseEntity {
  username: string;
  email: Email;
  first_name: string;
  last_name: string;
  full_name?: string;
  avatar_url?: Nullable<URL>;
  role: UserRole;
  is_active: boolean;
  last_login?: Nullable<Timestamp>;
  timezone?: string;
  preferences?: UserPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: {
    email: boolean;
    push: boolean;
    desktop: boolean;
  };
  dashboard: {
    default_view: 'grid' | 'list';
    items_per_page: number;
  };
}

export interface UserProfile extends Pick<User, 'first_name' | 'last_name' | 'email' | 'avatar_url' | 'timezone' | 'preferences'> {}

export interface CreateUser {
  username: string;
  email: Email;
  password: string;
  first_name: string;
  last_name: string;
  role?: UserRole;
}

export interface UpdateUser extends Partial<Omit<CreateUser, 'password'>> {
  current_password?: string;
  new_password?: string;
}

// ============= Authentication Types =============

export interface LoginCredentials {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  expires_at: Timestamp;
}

export interface TokenPayload {
  sub: string; // user ID
  username: string;
  role: UserRole;
  exp: number;
  iat: number;
  type: 'access' | 'refresh';
}

// ============= Project Types =============

export interface Project extends NamedEntity, OwnedEntity, MetadataEntity {
  slug: string;
  status: ProjectStatus;
  start_date?: Nullable<Timestamp>;
  end_date?: Nullable<Timestamp>;
  repository_url?: Nullable<URL>;
  documentation_url?: Nullable<URL>;
  tags: string[];
  member_count?: number;
  log_count?: number;
  file_count?: number;
}

export interface CreateProject {
  name: string;
  description?: string;
  status?: ProjectStatus;
  start_date?: Nullable<Timestamp>;
  end_date?: Nullable<Timestamp>;
  repository_url?: Nullable<URL>;
  documentation_url?: Nullable<URL>;
  tags?: string[];
}

export interface UpdateProject extends Partial<CreateProject> {}

export interface ProjectMember extends BaseEntity {
  project_id: ID;
  user_id: ID;
  role: UserRole;
  joined_at: Timestamp;
  user?: User;
}

export interface ProjectStats {
  total_logs: number;
  logs_this_week: number;
  logs_this_month: number;
  active_members: number;
  recent_activity: RecentActivity[];
}

// ============= Development Log Types =============

export interface DevelopmentLog extends BaseEntity, OwnedEntity, MetadataEntity {
  project_id: ID;
  title: string;
  content: string;
  category: LogCategory;
  priority: LogPriority;
  tags: string[];
  duration_minutes?: Nullable<number>;
  commit_hash?: Nullable<string>;
  branch_name?: Nullable<string>;
  pull_request_url?: Nullable<URL>;
  is_template: boolean;
  template_name?: Nullable<string>;
  version: number;
  
  // Relationships
  project?: Project;
  author?: User;
  attachments?: FileAttachment[];
  comments?: Comment[];
  
  // Computed fields
  comment_count?: number;
  attachment_count?: number;
}

export interface CreateDevelopmentLog {
  project_id: ID;
  title: string;
  content: string;
  category: LogCategory;
  priority?: LogPriority;
  tags?: string[];
  duration_minutes?: Nullable<number>;
  commit_hash?: Nullable<string>;
  branch_name?: Nullable<string>;
  pull_request_url?: Nullable<URL>;
  is_template?: boolean;
  template_name?: Nullable<string>;
}

export interface UpdateDevelopmentLog extends Partial<Omit<CreateDevelopmentLog, 'project_id'>> {}

export interface LogTemplate {
  id: ID;
  name: string;
  description?: string;
  category: LogCategory;
  content_template: string;
  default_tags: string[];
  is_public: boolean;
  usage_count: number;
}

// ============= Comment Types =============

export interface Comment extends BaseEntity, OwnedEntity {
  log_id: ID;
  parent_id?: Nullable<ID>;
  content: string;
  is_edited: boolean;
  edited_at?: Nullable<Timestamp>;
  
  // Relationships
  author?: User;
  replies?: Comment[];
  parent?: Comment;
  
  // Computed fields
  reply_count?: number;
}

export interface CreateComment {
  log_id: ID;
  parent_id?: Nullable<ID>;
  content: string;
}

export interface UpdateComment {
  content: string;
}

// ============= File Types =============

export interface FileAttachment extends BaseEntity, OwnedEntity {
  filename: string;
  original_filename: string;
  file_size: FileSize;
  content_type: string;
  file_path: string;
  download_url?: URL;
  preview_url?: URL;
  file_type: FileType;
  is_image: boolean;
  
  // For images
  width?: number;
  height?: number;
  
  // Relationships
  log_id?: Nullable<ID>;
  project_id?: Nullable<ID>;
  uploader?: User;
}

export interface FileUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  result?: FileAttachment;
}

// ============= API Response Types =============

export interface ApiResponse<T = any> {
  status: ResponseStatus;
  message: string;
  data?: T;
  meta?: Record<string, any>;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, any>;
}

export interface ErrorResponse {
  status: ResponseStatus.ERROR;
  message: string;
  error: ApiError;
  meta?: Record<string, any>;
}

export interface ValidationErrorDetail {
  field: string;
  message: string;
  rejected_value?: any;
  constraint?: string;
}

export interface ValidationErrorResponse extends ErrorResponse {
  validation_errors: ValidationErrorDetail[];
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  status: ResponseStatus.SUCCESS;
  message: string;
  data: T[];
  pagination: PaginationMeta;
  meta?: Record<string, any>;
}

// ============= Query and Filter Types =============

export interface BaseQuery {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

export interface ProjectQuery extends BaseQuery {
  status?: ProjectStatus;
  owner_id?: ID;
  tags?: string[];
  created_after?: Timestamp;
  created_before?: Timestamp;
}

export interface LogQuery extends BaseQuery {
  project_id?: ID;
  category?: LogCategory;
  priority?: LogPriority;
  author_id?: ID;
  tags?: string[];
  created_after?: Timestamp;
  created_before?: Timestamp;
  has_attachments?: boolean;
}

export interface UserQuery extends BaseQuery {
  role?: UserRole;
  is_active?: boolean;
  project_id?: ID;
}

// ============= UI State Types =============

export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
}

export interface FormState<T> extends LoadingState {
  data: T;
  isDirty: boolean;
  errors: Record<keyof T, string>;
}

export interface TableState<T> extends LoadingState {
  items: T[];
  pagination: PaginationMeta;
  query: BaseQuery;
  selectedItems: T[];
}

export interface ModalState {
  isOpen: boolean;
  mode: 'create' | 'edit' | 'view';
  data?: any;
}

// ============= Notification Types =============

export interface Notification {
  id: UUID;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Timestamp;
  isRead: boolean;
  action?: {
    label: string;
    url: string;
  };
}

export interface RecentActivity {
  id: ID;
  type: 'log_created' | 'log_updated' | 'comment_added' | 'file_uploaded' | 'member_added';
  title: string;
  description: string;
  timestamp: Timestamp;
  user: Pick<User, 'id' | 'username' | 'full_name' | 'avatar_url'>;
  resource_type: 'project' | 'log' | 'comment' | 'file';
  resource_id: ID;
  resource_url: string;
}

// ============= Analytics Types =============

export interface ActivityStats {
  period: 'day' | 'week' | 'month' | 'year';
  data: Array<{
    date: string;
    logs_created: number;
    comments_added: number;
    files_uploaded: number;
  }>;
}

export interface ProjectAnalytics {
  project_id: ID;
  total_logs: number;
  total_comments: number;
  total_files: number;
  active_contributors: number;
  activity_by_day: ActivityStats['data'];
  category_breakdown: Record<LogCategory, number>;
  priority_breakdown: Record<LogPriority, number>;
}

export interface UserAnalytics {
  user_id: ID;
  total_logs: number;
  total_comments: number;
  total_files: number;
  projects_contributed: number;
  activity_by_day: ActivityStats['data'];
  most_used_categories: Array<{
    category: LogCategory;
    count: number;
  }>;
}

// ============= Theme and UI Types =============

export interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    success: string;
    warning: string;
    error: string;
    info: string;
    background: string;
    surface: string;
    text: {
      primary: string;
      secondary: string;
      disabled: string;
    };
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  typography: {
    fontFamily: string;
    fontSize: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
  };
}

// ============= Export all types =============

// All types are already exported above via individual export statements
// This file serves as the central type definition hub for the PDLS frontend application