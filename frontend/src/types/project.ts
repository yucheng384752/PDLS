/**
 * Project Management Types for Phase 5
 * Detailed type definitions for project management components
 */

import { BaseEntity, ID, UUID, Timestamp, Email, URL } from './index';

// ============= Project Enums from Backend =============

export enum ProjectType {
  SOFTWARE = 'software',
  WEB = 'web',
  MOBILE = 'mobile',
  DATA_SCIENCE = 'data_science',
  INFRASTRUCTURE = 'infrastructure',
  RESEARCH = 'research',
  OTHER = 'other'
}

export enum ProjectStatus {
  PLANNING = 'planning',
  ACTIVE = 'active',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  ARCHIVED = 'archived'
}

export enum ProjectPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ProjectMemberRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer'
}

export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  DECLINED = 'declined',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired'
}

// ============= Core Project Interfaces =============

export interface Project extends BaseEntity {
  uuid: UUID;
  name: string;
  description?: string;
  project_type: ProjectType;
  status: ProjectStatus;
  priority: ProjectPriority;
  start_date?: Timestamp;
  end_date?: Timestamp;
  repository_url?: URL;
  documentation_url?: URL;
  tags: string[];
  
  // Ownership
  owner_id: ID;
  created_by: ID;
  
  // Statistics
  member_count: number;
  file_count: number;
  
  // Relationships (populated when needed)
  owner?: ProjectUser;
  creator?: ProjectUser;
  members?: ProjectMember[];
  files?: ProjectFile[];
  recent_activity?: ProjectActivity[];
}

export interface ProjectUser {
  id: ID;
  username: string;
  email: Email;
  full_name?: string;
  avatar_url?: URL;
  role?: string; // User role in system
}

export interface ProjectMember extends BaseEntity {
  project_id: ID;
  user_id: ID;
  role: ProjectMemberRole;
  joined_at: Timestamp;
  
  // Relationships
  user?: ProjectUser;
  project?: Project;
}

export interface ProjectFile extends BaseEntity {
  project_id: ID;
  filename: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  file_path: string;
  upload_url?: URL;
  download_url?: URL;
  
  // Ownership
  uploaded_by: ID;
  uploader?: ProjectUser;
}

export interface ProjectInvitation extends BaseEntity {
  project_id: ID;
  inviter_id: ID;
  invited_user_id?: ID;
  invited_email?: Email;
  role: ProjectMemberRole;
  status: InvitationStatus;
  message?: string;
  expires_at: Timestamp;
  
  // Relationships
  project?: Project;
  inviter?: ProjectUser;
  invited_user?: ProjectUser;
}

export interface ProjectActivity {
  id: ID;
  project_id: ID;
  user_id: ID;
  activity_type: 'project_created' | 'project_updated' | 'member_added' | 'member_removed' | 'file_uploaded' | 'invitation_sent';
  title: string;
  description: string;
  timestamp: Timestamp;
  
  // Relationships
  user?: ProjectUser;
  metadata?: Record<string, any>;
}

// ============= Create/Update DTOs =============

export interface CreateProjectRequest {
  name: string;
  description?: string;
  project_type: ProjectType;
  status?: ProjectStatus;
  priority?: ProjectPriority;
  start_date?: Timestamp;
  end_date?: Timestamp;
  repository_url?: URL;
  documentation_url?: URL;
  tags?: string[];
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  project_type?: ProjectType;
  status?: ProjectStatus;
  priority?: ProjectPriority;
  start_date?: Timestamp;
  end_date?: Timestamp;
  repository_url?: URL;
  documentation_url?: URL;
  tags?: string[];
}

export interface CreateInvitationRequest {
  project_id: ID;
  invited_user_id?: ID;
  invited_email?: Email;
  role: ProjectMemberRole;
  message?: string;
}

export interface UpdateMemberRoleRequest {
  role: ProjectMemberRole;
}

export interface FileUploadRequest {
  file: File;
  project_id: ID;
  description?: string;
}

// ============= Query and Filter Types =============

export interface ProjectListQuery {
  page?: number;
  page_size?: number;
  search?: string;
  project_type?: ProjectType;
  status?: ProjectStatus;
  priority?: ProjectPriority;
  owner_id?: ID;
  member_id?: ID;
  tags?: string[];
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'status' | 'priority';
  sort_order?: 'asc' | 'desc';
}

export interface ProjectMemberQuery {
  project_id: ID;
  role?: ProjectMemberRole;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface ProjectInvitationQuery {
  project_id?: ID;
  inviter_id?: ID;
  invited_user_id?: ID;
  status?: InvitationStatus;
  page?: number;
  page_size?: number;
}

export interface ProjectFileQuery {
  project_id: ID;
  search?: string;
  content_type?: string;
  uploaded_by?: ID;
  page?: number;
  page_size?: number;
  sort_by?: 'filename' | 'created_at' | 'file_size';
  sort_order?: 'asc' | 'desc';
}

// ============= Component State Types =============

export interface ProjectListState {
  projects: Project[];
  loading: boolean;
  error?: string;
  query: ProjectListQuery;
  total: number;
  selectedProjects: Project[];
}

export interface ProjectDetailState {
  project?: Project;
  members: ProjectMember[];
  files: ProjectFile[];
  invitations: ProjectInvitation[];
  activity: ProjectActivity[];
  loading: {
    project: boolean;
    members: boolean;
    files: boolean;
    invitations: boolean;
    activity: boolean;
  };
  error?: string;
}

export interface ProjectFormState {
  data: CreateProjectRequest;
  errors: Partial<Record<keyof CreateProjectRequest, string>>;
  loading: boolean;
  mode: 'create' | 'edit';
}

export interface InvitationFormState {
  data: CreateInvitationRequest;
  errors: Partial<Record<keyof CreateInvitationRequest, string>>;
  loading: boolean;
  searchResults: ProjectUser[];
  searchLoading: boolean;
}

export interface FileUploadState {
  files: Array<{
    file: File;
    progress: number;
    status: 'pending' | 'uploading' | 'completed' | 'error';
    error?: string;
    result?: ProjectFile;
  }>;
  uploading: boolean;
}

// ============= API Response Types =============

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectDetailResponse extends Project {
  members: ProjectMember[];
  recent_files: ProjectFile[];
  recent_activity: ProjectActivity[];
  statistics: {
    total_members: number;
    total_files: number;
    files_size: number;
    last_activity: Timestamp;
  };
}

export interface MemberListResponse {
  members: ProjectMember[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvitationListResponse {
  invitations: ProjectInvitation[];
  total: number;
  page: number;
  page_size: number;
}

export interface FileListResponse {
  files: ProjectFile[];
  total: number;
  total_size: number;
  page: number;
  page_size: number;
}

export interface ActivityListResponse {
  activities: ProjectActivity[];
  total: number;
  page: number;
  page_size: number;
}

// ============= UI Component Props Types =============

export interface ProjectCardProps {
  project: Project;
  onClick?: (project: Project) => void;
  onEdit?: (project: Project) => void;
  onDelete?: (project: Project) => void;
  showActions?: boolean;
  compact?: boolean;
}

export interface ProjectListProps {
  projects: Project[];
  loading?: boolean;
  onProjectSelect?: (project: Project) => void;
  onProjectEdit?: (project: Project) => void;
  onProjectDelete?: (project: Project) => void;
  onRefresh?: () => void;
  query?: ProjectListQuery;
  onQueryChange?: (query: ProjectListQuery) => void;
}

export interface ProjectFormProps {
  project?: Project;
  onSubmit: (data: CreateProjectRequest | UpdateProjectRequest) => void;
  onCancel?: () => void;
  loading?: boolean;
  errors?: Partial<Record<keyof CreateProjectRequest, string>>;
}

export interface ProjectDetailProps {
  projectId: ID;
  project?: Project;
  onProjectUpdate?: (project: Project) => void;
}

export interface MemberListProps {
  projectId: ID;
  members: ProjectMember[];
  currentUserRole?: ProjectMemberRole;
  onInviteMember?: () => void;
  onRemoveMember?: (member: ProjectMember) => void;
  onUpdateRole?: (member: ProjectMember, role: ProjectMemberRole) => void;
  loading?: boolean;
}

export interface InvitationFormProps {
  projectId: ID;
  onSubmit: (data: CreateInvitationRequest) => void;
  onCancel?: () => void;
  loading?: boolean;
  errors?: Partial<Record<keyof CreateInvitationRequest, string>>;
}

export interface FileManagerProps {
  projectId: ID;
  files: ProjectFile[];
  onUpload?: (files: File[]) => void;
  onDownload?: (file: ProjectFile) => void;
  onDelete?: (file: ProjectFile) => void;
  loading?: boolean;
  uploadProgress?: FileUploadState;
}

// ============= Error Types =============

export interface ProjectError {
  code: string;
  message: string;
  field?: keyof CreateProjectRequest | keyof UpdateProjectRequest;
  details?: any;
}

export interface ValidationError {
  field: string;
  message: string;
  code?: string;
}

// ============= Permission Types =============

export interface ProjectPermissions {
  can_view: boolean;
  can_edit: boolean;
  can_delete: boolean;
  can_manage_members: boolean;
  can_invite_members: boolean;
  can_upload_files: boolean;
  can_delete_files: boolean;
  can_change_settings: boolean;
}

export interface UserProjectRole {
  project_id: ID;
  user_id: ID;
  role: ProjectMemberRole;
  permissions: ProjectPermissions;
  joined_at: Timestamp;
}

// ============= Dashboard Types =============

export interface ProjectDashboardData {
  my_projects: Project[];
  recent_projects: Project[];
  project_statistics: {
    total_projects: number;
    active_projects: number;
    projects_as_owner: number;
    projects_as_member: number;
  };
  recent_activity: ProjectActivity[];
  upcoming_deadlines: Array<{
    project: Project;
    end_date: Timestamp;
    days_remaining: number;
  }>;
}

// ============= Export all project types =============
export type {
  // Core interfaces are already exported via individual exports above
};