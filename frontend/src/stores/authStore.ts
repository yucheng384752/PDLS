/**
 * Authentication state management using Zustand
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, LoginRequest, RegisterRequest, PasswordChangeRequest } from '../types/user';
import { AuthService } from '../services/userService';

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  changePassword: (data: PasswordChangeRequest) => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login action
      login: async (credentials: LoginRequest) => {
        try {
          set({ isLoading: true, error: null });
          
          const authResponse = await AuthService.login(credentials);
          
          set({
            user: authResponse.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: error?.response?.data?.message || error?.message || 'Login failed',
          });
          throw error;
        }
      },

      // Register action
      register: async (userData: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });
          
          const authResponse = await AuthService.register(userData);
          
          set({
            user: authResponse.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: error?.response?.data?.message || error?.message || 'Registration failed',
          });
          throw error;
        }
      },

      // Logout action
      logout: async () => {
        try {
          await AuthService.logout();
        } catch (error) {
          // Continue with logout even if API call fails
          console.warn('Logout API call failed:', error);
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      // Refresh user data
      refreshUser: async () => {
        try {
          if (!AuthService.isAuthenticated()) {
            set({
              user: null,
              isAuthenticated: false,
              error: null,
            });
            return;
          }

          set({ isLoading: true });
          
          const user = await AuthService.getCurrentUser();
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          // If token is invalid, clear authentication
          if (error?.response?.status === 401) {
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: null,
            });
          } else {
            set({
              isLoading: false,
              error: error?.response?.data?.message || error?.message || 'Failed to refresh user data',
            });
          }
        }
      },

      // Change password
      changePassword: async (data: PasswordChangeRequest) => {
        try {
          set({ isLoading: true, error: null });
          
          await AuthService.changePassword(data);
          
          set({ isLoading: false, error: null });
        } catch (error: any) {
          set({
            isLoading: false,
            error: error?.response?.data?.message || error?.message || 'Password change failed',
          });
          throw error;
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Set loading state
      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors for easier state access
export const useAuth = () => {
  const { user, isAuthenticated, isLoading, error } = useAuthStore();
  return { user, isAuthenticated, isLoading, error };
};

export const useAuthActions = () => {
  const { login, register, logout, refreshUser, changePassword, clearError } = useAuthStore();
  return { login, register, logout, refreshUser, changePassword, clearError };
};

// Helper hooks
export const useCurrentUser = () => {
  return useAuthStore((state) => state.user);
};

export const useIsAuthenticated = () => {
  return useAuthStore((state) => state.isAuthenticated);
};

export const useAuthError = () => {
  return useAuthStore((state) => state.error);
};

export const useAuthLoading = () => {
  return useAuthStore((state) => state.isLoading);
};