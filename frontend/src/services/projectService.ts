/**
 * Project Management API Service
 * Provides all project-related API operations for Phase 5
 */

import { apiClient } from './api';
import { ID, UUID } from '../types/index';
import {
  Project,
  ProjectMember,
  ProjectFile,
  ProjectInvitation,
  ProjectActivity,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateInvitationRequest,
  UpdateMemberRoleRequest,
  FileUploadRequest,
  ProjectListQuery,
  ProjectMemberQuery,
  ProjectInvitationQuery,
  ProjectFileQuery,
  ProjectListResponse,
  ProjectDetailResponse,
  MemberListResponse,
  InvitationListResponse,
  FileListResponse,
  ActivityListResponse,
  ProjectDashboardData,
} from '../types/project';

export class ProjectService {
  private readonly baseUrl = '/projects';

  // ============= Project CRUD Operations =============

  /**
   * Get paginated list of projects
   */
  async getProjects(query?: ProjectListQuery): Promise<ProjectListResponse> {
    const response = await apiClient.getPaginated<Project>(`${this.baseUrl}/simple`, query);
    return {
      projects: response.data,
      total: response.pagination.total_items,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
      total_pages: response.pagination.total_pages,
    };
  }

  /**
   * Get project by ID with detailed information
   */
  async getProject(projectId: ID): Promise<ProjectDetailResponse> {
    const response = await apiClient.get<ProjectDetailResponse>(`${this.baseUrl}/simple/${projectId}`);
    return response.data!;
  }

  /**
   * Get project by UUID
   */
  async getProjectByUuid(uuid: UUID): Promise<ProjectDetailResponse> {
    const response = await apiClient.get<ProjectDetailResponse>(`${this.baseUrl}/uuid/${uuid}`);
    return response.data!;
  }

  /**
   * Create new project
   */
  async createProject(data: CreateProjectRequest): Promise<Project> {
    const response = await apiClient.post<Project>(`${this.baseUrl}/simple`, data);
    return response.data!;
  }

  /**
   * Update existing project
   */
  async updateProject(projectId: ID, data: UpdateProjectRequest): Promise<Project> {
    const response = await apiClient.put<Project>(`${this.baseUrl}/simple/${projectId}`, data);
    return response.data!;
  }

  /**
   * Delete project (soft delete)
   */
  async deleteProject(projectId: ID): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/simple/${projectId}`);
  }

  /**
   * Archive project
   */
  async archiveProject(projectId: ID): Promise<Project> {
    const response = await apiClient.patch<Project>(`${this.baseUrl}/${projectId}/archive`);
    return response.data!;
  }

  /**
   * Restore archived project
   */
  async restoreProject(projectId: ID): Promise<Project> {
    const response = await apiClient.patch<Project>(`${this.baseUrl}/${projectId}/restore`);
    return response.data!;
  }

  // ============= Project Member Management =============

  /**
   * Get project members
   */
  async getProjectMembers(query: ProjectMemberQuery): Promise<MemberListResponse> {
    const { project_id, ...params } = query;
    const response = await apiClient.getPaginated<ProjectMember>(
      `${this.baseUrl}/${project_id}/members`,
      params
    );
    return {
      members: response.data,
      total: response.pagination.total_items,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
    };
  }

  /**
   * Add member to project (direct add, not via invitation)
   */
  async addProjectMember(projectId: ID, userId: ID, role: string): Promise<ProjectMember> {
    const response = await apiClient.post<ProjectMember>(
      `${this.baseUrl}/${projectId}/members`,
      { user_id: userId, role }
    );
    return response.data!;
  }

  /**
   * Update member role
   */
  async updateMemberRole(
    projectId: ID,
    memberId: ID,
    data: UpdateMemberRoleRequest
  ): Promise<ProjectMember> {
    const response = await apiClient.put<ProjectMember>(
      `${this.baseUrl}/${projectId}/members/${memberId}`,
      data
    );
    return response.data!;
  }

  /**
   * Remove member from project
   */
  async removeMember(projectId: ID, memberId: ID): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${projectId}/members/${memberId}`);
  }

  /**
   * Leave project (current user)
   */
  async leaveProject(projectId: ID): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${projectId}/leave`);
  }

  // ============= Project Invitations =============

  /**
   * Get project invitations
   */
  async getInvitations(query: ProjectInvitationQuery): Promise<InvitationListResponse> {
    let url = '/invitations';
    if (query.project_id) {
      url = `${this.baseUrl}/${query.project_id}/invitations`;
    }

    const { project_id, ...params } = query;
    const response = await apiClient.getPaginated<ProjectInvitation>(url, params);
    
    return {
      invitations: response.data,
      total: response.pagination.total_items,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
    };
  }

  /**
   * Send project invitation
   */
  async sendInvitation(data: CreateInvitationRequest): Promise<ProjectInvitation> {
    const response = await apiClient.post<ProjectInvitation>('/invitations', data);
    return response.data!;
  }

  /**
   * Accept invitation
   */
  async acceptInvitation(invitationId: ID): Promise<ProjectMember> {
    const response = await apiClient.post<ProjectMember>(`/invitations/${invitationId}/accept`);
    return response.data!;
  }

  /**
   * Decline invitation
   */
  async declineInvitation(invitationId: ID): Promise<void> {
    await apiClient.post(`/invitations/${invitationId}/decline`);
  }

  /**
   * Cancel invitation (inviter only)
   */
  async cancelInvitation(invitationId: ID): Promise<void> {
    await apiClient.delete(`/invitations/${invitationId}`);
  }

  /**
   * Resend invitation
   */
  async resendInvitation(invitationId: ID): Promise<ProjectInvitation> {
    const response = await apiClient.post<ProjectInvitation>(`/invitations/${invitationId}/resend`);
    return response.data!;
  }

  // ============= File Management =============

  /**
   * Get project files
   */
  async getProjectFiles(query: ProjectFileQuery): Promise<FileListResponse> {
    const { project_id, ...params } = query;
    const response = await apiClient.getPaginated<ProjectFile>(
      `${this.baseUrl}/${project_id}/files`,
      params
    );

    const totalSize = response.data.reduce((sum, file) => sum + file.file_size, 0);

    return {
      files: response.data,
      total: response.pagination.total_items,
      total_size: totalSize,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
    };
  }

  /**
   * Upload file to project
   */
  async uploadFile(
    data: FileUploadRequest,
    onProgress?: (progress: number) => void
  ): Promise<ProjectFile> {
    const response = await apiClient.uploadFile<ProjectFile>(
      `${this.baseUrl}/${data.project_id}/files`,
      data.file,
      onProgress
    );
    return response.data!;
  }

  /**
   * Get file download URL
   */
  async getFileDownloadUrl(projectId: ID, fileId: ID): Promise<string> {
    const response = await apiClient.get<{ download_url: string }>(
      `${this.baseUrl}/${projectId}/files/${fileId}/download`
    );
    return response.data!.download_url;
  }

  /**
   * Delete file
   */
  async deleteFile(projectId: ID, fileId: ID): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${projectId}/files/${fileId}`);
  }

  /**
   * Update file metadata
   */
  async updateFile(
    projectId: ID,
    fileId: ID,
    data: { filename?: string; description?: string }
  ): Promise<ProjectFile> {
    const response = await apiClient.patch<ProjectFile>(
      `${this.baseUrl}/${projectId}/files/${fileId}`,
      data
    );
    return response.data!;
  }

  // ============= Project Activity =============

  /**
   * Get project activity feed
   */
  async getProjectActivity(projectId: ID, page = 1, pageSize = 20): Promise<ActivityListResponse> {
    const response = await apiClient.getPaginated<ProjectActivity>(
      `${this.baseUrl}/${projectId}/activity`,
      { page, page_size: pageSize }
    );

    return {
      activities: response.data,
      total: response.pagination.total_items,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
    };
  }

  // ============= Project Statistics =============

  /**
   * Get project statistics
   */
  async getProjectStatistics(projectId: ID): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/${projectId}/statistics`);
    return response.data;
  }

  /**
   * Get project analytics
   */
  async getProjectAnalytics(projectId: ID, period?: string): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/${projectId}/analytics`, {
      params: { period }
    });
    return response.data;
  }

  // ============= Dashboard and Overview =============

  /**
   * Get project dashboard data for current user
   */
  async getDashboardData(): Promise<ProjectDashboardData> {
    const response = await apiClient.get<ProjectDashboardData>('/dashboard/projects');
    return response.data!;
  }

  /**
   * Get user's project summary
   */
  async getUserProjectSummary(userId?: ID): Promise<any> {
    const url = userId ? `/users/${userId}/projects/summary` : '/me/projects/summary';
    const response = await apiClient.get(url);
    return response.data;
  }

  // ============= Search and Discovery =============

  /**
   * Search projects
   */
  async searchProjects(query: string, filters?: Partial<ProjectListQuery>): Promise<ProjectListResponse> {
    const response = await apiClient.getPaginated<Project>(`${this.baseUrl}/search`, {
      q: query,
      ...filters
    });

    return {
      projects: response.data,
      total: response.pagination.total_items,
      page: response.pagination.page,
      page_size: response.pagination.page_size,
      total_pages: response.pagination.total_pages,
    };
  }

  /**
   * Get project suggestions for current user
   */
  async getProjectSuggestions(limit = 5): Promise<Project[]> {
    const response = await apiClient.get<Project[]>(`${this.baseUrl}/suggestions`, {
      params: { limit }
    });
    return response.data || [];
  }

  /**
   * Search users for project invitations
   */
  async searchUsersForInvitation(projectId: ID, query: string): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${projectId}/users/search`, {
      params: { q: query }
    });
    return response.data || [];
  }

  // ============= Bulk Operations =============

  /**
   * Bulk update projects
   */
  async bulkUpdateProjects(projectIds: ID[], updates: Partial<UpdateProjectRequest>): Promise<void> {
    await apiClient.patch(`${this.baseUrl}/bulk`, {
      project_ids: projectIds,
      updates
    });
  }

  /**
   * Bulk delete projects
   */
  async bulkDeleteProjects(projectIds: ID[]): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/bulk`, {
      data: { project_ids: projectIds }
    });
  }

  /**
   * Export projects data
   */
  async exportProjects(projectIds: ID[], format: 'json' | 'csv' | 'excel' = 'json'): Promise<Blob> {
    const response = await apiClient.getAxiosInstance().post(`${this.baseUrl}/export`, 
      { project_ids: projectIds, format },
      { responseType: 'blob' }
    );
    return response.data;
  }

  // ============= Utility Methods =============

  /**
   * Check if project name is available
   */
  async checkProjectNameAvailability(name: string, excludeProjectId?: ID): Promise<boolean> {
    const response = await apiClient.get<{ available: boolean }>(`${this.baseUrl}/check-name`, {
      params: { name, exclude_id: excludeProjectId }
    });
    return response.data!.available;
  }

  /**
   * Get project tags suggestions
   */
  async getTagSuggestions(query?: string): Promise<string[]> {
    const response = await apiClient.get<string[]>(`${this.baseUrl}/tags`, {
      params: { q: query }
    });
    return response.data || [];
  }

  /**
   * Validate project data
   */
  async validateProject(data: CreateProjectRequest | UpdateProjectRequest): Promise<any> {
    const response = await apiClient.post('/validation/project', data);
    return response.data;
  }
}

// Create and export default instance
export const projectService = new ProjectService();

// Export class for custom instances
export default ProjectService;