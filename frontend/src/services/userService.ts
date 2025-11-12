/**
 * User management API services
 */

import { apiClient } from './api';
import type {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  PasswordResetRequest,
  PasswordResetConfirm,
  PasswordChangeRequest,
  UserCreateRequest,
  UserUpdateRequest,
  UserRoleUpdateRequest,
  UserListParams,
  UserListResponse,
  UserPermissions,
  UserProfile,
  UpdateUserProfile,
  ChangePassword,
} from '../types/user';


export class AuthService {
  /**
   * User login
   */
  static async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', data);
    
    if (response.data) {
      // Store authentication tokens
      apiClient.setAuthentication(
        response.data.access_token,
        response.data.refresh_token
      );
    }
    
    return response.data!;
  }

  /**
   * User registration
   */
  static async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/register', data);
    
    if (response.data) {
      // Store authentication tokens
      apiClient.setAuthentication(
        response.data.access_token,
        response.data.refresh_token
      );
    }
    
    return response.data!;
  }

  /**
   * User logout
   */
  static async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      // Clear authentication regardless of API response
      apiClient.clearAuthentication();
    }
  }

  /**
   * Request password reset
   */
  static async requestPasswordReset(data: PasswordResetRequest): Promise<void> {
    await apiClient.post('/auth/forgot-password', data);
  }

  /**
   * Confirm password reset
   */
  static async confirmPasswordReset(data: PasswordResetConfirm): Promise<void> {
    await apiClient.post('/auth/reset-password', data);
  }

  /**
   * Change password
   */
  static async changePassword(data: PasswordChangeRequest): Promise<void> {
    await apiClient.post('/auth/change-password', data);
  }

  /**
   * Change user password (extended version)
   */
  static async changeUserPassword(data: ChangePassword): Promise<void> {
    await apiClient.post('/users/change-password', data);
  }

  /**
   * Verify email
   */
  static async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/auth/verify-email', { token });
  }

  /**
   * Refresh authentication token
   */
  static async refreshToken(): Promise<AuthResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiClient.post<AuthResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });

    if (response.data) {
      apiClient.setAuthentication(
        response.data.access_token,
        response.data.refresh_token
      );
    }

    return response.data!;
  }

  /**
   * Get current user info
   */
  static async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/users/me');
    return response.data!;
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    return apiClient.isAuthenticated();
  }
}

class UserService {
  /**
   * Get current user profile
   */
  static async getProfile(): Promise<User> {
    const response = await apiClient.get<User>('/users/me');
    return response.data!;
  }

  /**
   * Get user profile by ID
   */
  static async getUserProfile(userId: string): Promise<UserProfile> {
    const response = await apiClient.get<UserProfile>(`/users/${userId}/profile`);
    return response.data!;
  }

  /**
   * Update current user profile
   */
  static async updateProfile(data: UserUpdateRequest): Promise<User> {
    const response = await apiClient.put<User>('/users/me', data);
    return response.data!;
  }

  /**
   * Update user profile by ID
   */
  static async updateUserProfile(userId: string, data: UpdateUserProfile): Promise<UserProfile> {
    const response = await apiClient.put<UserProfile>(`/users/${userId}/profile`, data);
    return response.data!;
  }

  /**
   * Get user by ID
   */
  static async getUserById(id: number): Promise<User> {
    const response = await apiClient.get<User>(`/users/${id}`);
    return response.data!;
  }

  /**
   * Get users list with filtering and pagination
   */
  static async getUsers(params: UserListParams = {}): Promise<UserListResponse> {
    const response = await apiClient.get<UserListResponse>('/users', { params });
    return response.data!;
  }

  /**
   * Create new user
   */
  static async createUser(data: UserCreateRequest): Promise<User> {
    const response = await apiClient.post<User>('/users', data);
    return response.data!;
  }

  /**
   * Update user
   */
  static async updateUser(id: number, data: UserUpdateRequest): Promise<User> {
    const response = await apiClient.put<User>(`/users/${id}`, data);
    return response.data!;
  }

  /**
   * Update user role
   */
  static async updateUserRole(id: number, data: UserRoleUpdateRequest): Promise<User> {
    const response = await apiClient.put<User>(`/users/${id}/role`, data);
    return response.data!;
  }

  /**
   * Delete user
   */
  static async deleteUser(id: number): Promise<void> {
    await apiClient.delete(`/users/${id}`);
  }

  /**
   * Get user permissions
   */
  static async getUserPermissions(id: number): Promise<UserPermissions> {
    const response = await apiClient.get<UserPermissions>(`/users/${id}/permissions`);
    return response.data!;
  }

  /**
   * Upload user avatar
   */
  static async uploadAvatar(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<{ avatar_url: string }> {
    const response = await apiClient.uploadFile<{ avatar_url: string }>(
      '/users/me/avatar',
      file,
      onProgress
    );
    return response.data!;
  }

  /**
   * Delete user avatar
   */
  static async deleteAvatar(): Promise<void> {
    await apiClient.delete('/users/me/avatar');
  }
}

// Export all services
export { AuthService as default, UserService };