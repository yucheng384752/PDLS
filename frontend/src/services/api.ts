/**
 * API client with interceptors for PDLS frontend
 * Provides centralized HTTP client with authentication, error handling, and request/response interception
 */

import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  AxiosResponse, 
  AxiosError,
  InternalAxiosRequestConfig 
} from 'axios';
import { toast } from 'react-toastify';

// Types for API responses
export interface ApiResponse<T = any> {
  status: 'success' | 'error' | 'warning' | 'partial';
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
  status: 'error';
  message: string;
  error: ApiError;
  meta?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  status: 'success';
  message: string;
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
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

// Configuration interface
export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  enableToasts?: boolean;
  enableRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

class ApiClient {
  private instance: AxiosInstance;
  private config: Required<ApiClientConfig>;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
  }> = [];

  constructor(config: ApiClientConfig = {}) {
    this.config = {
      baseURL: config.baseURL || import.meta.env.VITE_API_BASE_URL || '/api/v1',
      timeout: config.timeout || 30000,
      enableToasts: config.enableToasts !== false,
      enableRetry: config.enableRetry !== false,
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
    };

    this.instance = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.instance.interceptors.request.use(
      this.onRequestFulfilled.bind(this),
      this.onRequestRejected.bind(this)
    );

    // Response interceptor
    this.instance.interceptors.response.use(
      this.onResponseFulfilled.bind(this),
      this.onResponseRejected.bind(this)
    );
  }

  private onRequestFulfilled(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
    // Add authentication token if available
    const token = this.getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add request ID for tracking
    config.headers['X-Request-ID'] = this.generateRequestId();

    // Add timestamp
    config.headers['X-Client-Timestamp'] = new Date().toISOString();

    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data,
      });
    }

    return config;
  }

  private onRequestRejected(error: AxiosError): Promise<AxiosError> {
    console.error('Request error:', error);
    return Promise.reject(error);
  }

  private onResponseFulfilled(response: AxiosResponse): AxiosResponse {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log(`✅ API Response: ${response.status} ${response.config.url}`, {
        data: response.data,
        headers: response.headers,
      });
    }

    // Show success toast for write operations if enabled
    if (this.config.enableToasts && this.isWriteOperation(response.config.method)) {
      const apiResponse = response.data as ApiResponse;
      if (apiResponse.status === 'success' && apiResponse.message) {
        toast.success(apiResponse.message);
      }
    }

    return response;
  }

  private async onResponseRejected(error: AxiosError): Promise<any> {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Log error in development
    if (import.meta.env.DEV) {
      console.error(`❌ API Error: ${error.response?.status} ${originalRequest?.url}`, {
        error: error.response?.data,
        headers: error.response?.headers,
      });
    }

    // Handle token refresh for 401 errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (this.isRefreshing) {
        // If already refreshing, queue the request
        return new Promise((resolve, reject) => {
          this.failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers!.Authorization = `Bearer ${token}`;
          return this.instance(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      this.isRefreshing = true;

      try {
        const newToken = await this.refreshToken();
        this.processFailedQueue(newToken, null);
        originalRequest.headers!.Authorization = `Bearer ${newToken}`;
        return this.instance(originalRequest);
      } catch (refreshError) {
        this.processFailedQueue(null, refreshError);
        this.handleAuthenticationError();
        return Promise.reject(refreshError);
      } finally {
        this.isRefreshing = false;
      }
    }

    // Handle retry logic for network errors
    if (this.config.enableRetry && this.shouldRetry(error)) {
      const retryCount = (originalRequest as any).__retryCount || 0;
      if (retryCount < this.config.maxRetries) {
        (originalRequest as any).__retryCount = retryCount + 1;
        
        await this.delay(this.config.retryDelay * Math.pow(2, retryCount));
        return this.instance(originalRequest);
      }
    }

    // Handle and display errors
    this.handleError(error);
    return Promise.reject(error);
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private setAuthToken(token: string): void {
    localStorage.setItem('auth_token', token);
  }

  private removeAuthToken(): void {
    localStorage.removeItem('auth_token');
  }

  private async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await axios.post(`${this.config.baseURL}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken } = response.data.data;
      this.setAuthToken(access_token);
      localStorage.setItem('refresh_token', newRefreshToken);

      return access_token;
    } catch (error) {
      this.removeAuthToken();
      localStorage.removeItem('refresh_token');
      throw error;
    }
  }

  private processFailedQueue(token: string | null, error: any): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });
    
    this.failedQueue = [];
  }

  private handleAuthenticationError(): void {
    this.removeAuthToken();
    localStorage.removeItem('refresh_token');
    
    if (this.config.enableToasts) {
      toast.error('Session expired. Please login again.');
    }
    
    // Redirect to login page
    window.location.href = '/login';
  }

  private handleError(error: AxiosError): void {
    if (!this.config.enableToasts) return;

    const response = error.response;
    if (!response) {
      toast.error('Network error. Please check your connection.');
      return;
    }

    const errorData = response.data as ErrorResponse;
    
    switch (response.status) {
      case 400:
        toast.error(errorData?.error?.message || 'Bad request');
        break;
      case 401:
        // Handled by authentication logic
        break;
      case 403:
        toast.error('Access denied. Insufficient permissions.');
        break;
      case 404:
        toast.error('Resource not found');
        break;
      case 409:
        toast.error(errorData?.error?.message || 'Conflict error');
        break;
      case 422:
        if ('validation_errors' in errorData) {
          const validationError = errorData as ValidationErrorResponse;
          validationError.validation_errors.forEach(err => {
            toast.error(`${err.field}: ${err.message}`);
          });
        } else {
          toast.error(errorData?.error?.message || 'Validation error');
        }
        break;
      case 429:
        toast.error('Too many requests. Please try again later.');
        break;
      case 500:
        toast.error('Server error. Please try again later.');
        break;
      default:
        toast.error(errorData?.error?.message || 'An unexpected error occurred');
    }
  }

  private shouldRetry(error: AxiosError): boolean {
    // Retry on network errors or 5xx server errors
    return !error.response || (error.response.status >= 500 && error.response.status < 600);
  }

  private isWriteOperation(method?: string): boolean {
    return ['post', 'put', 'patch', 'delete'].includes(method?.toLowerCase() || '');
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Public API methods
  public async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.get(url, config);
    return response.data;
  }

  public async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.post(url, data, config);
    return response.data;
  }

  public async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.put(url, data, config);
    return response.data;
  }

  public async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.patch(url, data, config);
    return response.data;
  }

  public async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.delete(url, config);
    return response.data;
  }

  // Upload file with progress
  public async uploadFile<T = any>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<T>> {
    const formData = new FormData();
    formData.append('file', file);

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    };

    const response = await this.instance.post(url, formData, config);
    return response.data;
  }

  // Paginated request
  public async getPaginated<T = any>(
    url: string,
    params?: Record<string, any>
  ): Promise<PaginatedResponse<T>> {
    const response = await this.instance.get(url, { params });
    return response.data;
  }

  // Authentication methods
  public setAuthentication(accessToken: string, refreshToken?: string): void {
    this.setAuthToken(accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  public clearAuthentication(): void {
    this.removeAuthToken();
    localStorage.removeItem('refresh_token');
  }

  public isAuthenticated(): boolean {
    return !!this.getAuthToken();
  }

  // Get raw axios instance for advanced usage
  public getAxiosInstance(): AxiosInstance {
    return this.instance;
  }
}

// Create and export default API client instance
export const apiClient = new ApiClient();

// Export class for creating custom instances
export default ApiClient;