/**
 * Login Form Component using PrimeReact
 */

import React, { useState, useRef } from 'react';
import { Navigate, Link, useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { ProgressSpinner } from 'primereact/progressspinner';
import { classNames } from 'primereact/utils';
import './LoginForm.css';

// Types
interface LoginFormData {
  username: string;
  password: string;
  rememberMe: boolean;
}

// Validation schema
const loginSchema = yup.object({
  username: yup
    .string()
    .required('用戶名是必填項目')
    .min(3, '用戶名至少需要 3 個字符'),
  password: yup
    .string()
    .required('密碼是必填項目')
    .min(6, '密碼至少需要 6 個字符'),
  rememberMe: yup.boolean(),
});

interface LoginFormProps {
  onSubmit?: (data: LoginFormData) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onSubmit,
  isLoading = false,
  error,
  className = '',
}) => {
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Form setup
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    clearErrors,
  } = useForm<LoginFormData>({
    resolver: yupResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false,
    },
  });

  // Handle form submission
  const handleFormSubmit = async (data: LoginFormData) => {
    try {
      clearErrors();
      
      if (onSubmit) {
        await onSubmit(data);
      } else {
        // Default implementation - you can replace this with your auth logic
        console.log('Login attempt:', { username: data.username, rememberMe: data.rememberMe });
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        toast.current?.show({
          severity: 'success',
          summary: '登入成功',
          detail: `歡迎回來，${data.username}！`,
          life: 3000,
        });
        
        // Navigate to dashboard or intended destination
        navigate('/dashboard');
      }
    } catch (err: any) {
      console.error('Login error:', err);
      
      const errorMessage = err?.response?.data?.message || err?.message || '登入失敗，請重試';
      
      toast.current?.show({
        severity: 'error',
        summary: '登入失敗',
        detail: errorMessage,
        life: 5000,
      });
      
      // Set form error if it's a validation error
      if (err?.response?.status === 400) {
        setError('username', { message: '用戶名或密碼錯誤' });
      }
    }
  };

  // Show error toast if error prop changes
  React.useEffect(() => {
    if (error) {
      toast.current?.show({
        severity: 'error',
        summary: '登入失敗',
        detail: error,
        life: 5000,
      });
    }
  }, [error]);

  // Helper function to get form error message
  const getFormErrorMessage = (name: keyof LoginFormData) => {
    return errors[name] && (
      <small className="p-error block mt-1">
        {errors[name]?.message}
      </small>
    );
  };

  return (
    <div className={`login-form-container ${className}`}>
      <Toast ref={toast} />
      
      <Card className="login-card shadow-3">
        <div className="login-header text-center mb-4">
          <div className="login-logo mb-3">
            <i className="pi pi-code text-6xl text-primary"></i>
          </div>
          <h2 className="text-900 text-3xl font-medium mb-2">
            項目開發日誌系統
          </h2>
          <p className="text-600 text-lg mb-0">
            請登入您的帳戶
          </p>
        </div>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="login-form">
          {/* Username Field */}
          <div className="field mb-4">
            <label htmlFor="username" className="block text-900 font-medium mb-2">
              用戶名 *
            </label>
            <Controller
              name="username"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <InputText
                    id="username"
                    {...field}
                    placeholder="請輸入用戶名"
                    className={classNames(
                      'w-full p-3',
                      { 'p-invalid': fieldState.error }
                    )}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('username')}
                </>
              )}
            />
          </div>

          {/* Password Field */}
          <div className="field mb-4">
            <label htmlFor="password" className="block text-900 font-medium mb-2">
              密碼 *
            </label>
            <Controller
              name="password"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <Password
                    id="password"
                    {...field}
                    placeholder="請輸入密碼"
                    className={classNames(
                      'w-full',
                      { 'p-invalid': fieldState.error }
                    )}
                    inputClassName="w-full p-3"
                    toggleMask
                    feedback={false}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('password')}
                </>
              )}
            />
          </div>

          {/* Remember Me Checkbox */}
          <div className="field mb-4">
            <Controller
              name="rememberMe"
              control={control}
              render={({ field }) => (
                <div className="flex align-items-center">
                  <Checkbox
                    id="rememberMe"
                    checked={field.value}
                    onChange={(e) => field.onChange(e.checked)}
                    disabled={isLoading || isSubmitting}
                    className="mr-2"
                  />
                  <label htmlFor="rememberMe" className="text-900 cursor-pointer">
                    記住我的登入狀態
                  </label>
                </div>
              )}
            />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            label="登入"
            className="w-full p-3 text-xl font-bold"
            disabled={isLoading || isSubmitting}
            loading={isLoading || isSubmitting}
          />

          {/* Forgot Password Link */}
          <div className="text-center mt-4">
            <Link 
              to="/forgot-password"
              className="text-primary hover:text-primary-700 text-sm no-underline"
            >
              忘記密碼？
            </Link>
          </div>

          <Divider align="center" className="my-4">
            <span className="text-600 text-sm">或</span>
          </Divider>

          {/* Register Link */}
          <div className="text-center">
            <span className="text-600 text-sm mr-2">還沒有帳戶？</span>
            <Link 
              to="/register"
              className="text-primary hover:text-primary-700 text-sm no-underline font-medium"
            >
              立即註冊
            </Link>
          </div>
        </form>
      </Card>

      {/* Loading Overlay */}
      {(isLoading || isSubmitting) && (
        <div className="loading-overlay">
          <ProgressSpinner 
            style={{ width: '50px', height: '50px' }} 
            strokeWidth="4" 
          />
        </div>
      )}
    </div>
  );
};

export default LoginForm;