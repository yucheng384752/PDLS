/**
 * User components exports
 * Centralizes all user-related component imports for easier usage
 */

// Authentication components
export { LoginForm } from './LoginForm';
export { RegisterForm } from './RegisterForm';

// User management components
export { UserProfile } from './UserProfile';
export { UserManagement } from './UserManagement';
export { AvatarUpload } from './AvatarUpload';

// Re-export types for convenience
export type {
  User,
  UserRole,
  UserStatus,
  UserProfile as UserProfileType,
  UpdateUserProfile,
  ChangePassword,
  LoginRequest,
  RegisterRequest,
  AuthResponse
} from '../../types/user';

// Re-export services
export { AuthService, UserService } from '../../services/userService';

// Re-export store
export { useAuthStore } from '../../stores/authStore';