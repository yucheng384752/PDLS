/**
 * Register Form Component using PrimeReact
 */

import React, { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { Dropdown } from 'primereact/dropdown';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { ProgressSpinner } from 'primereact/progressspinner';
import { classNames } from 'primereact/utils';
import { TIMEZONE_OPTIONS, LANGUAGE_OPTIONS } from '../../types/user';
import './RegisterForm.css';

// Types
interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  phone?: string;
  timezone: string;
  language: string;
  acceptTerms: boolean;
}

// Validation schema
const registerSchema = yup.object({
  username: yup
    .string()
    .required('用戶名是必填項目')
    .min(3, '用戶名至少需要 3 個字符')
    .max(50, '用戶名最多 50 個字符')
    .matches(/^[a-zA-Z0-9_-]+$/, '用戶名只能包含字母、數字、底線和連字符'),
  email: yup
    .string()
    .required('電子郵件是必填項目')
    .email('請輸入有效的電子郵件地址'),
  password: yup
    .string()
    .required('密碼是必填項目')
    .min(8, '密碼至少需要 8 個字符')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      '密碼必須包含至少一個小寫字母、一個大寫字母和一個數字'
    ),
  confirmPassword: yup
    .string()
    .required('確認密碼是必填項目')
    .oneOf([yup.ref('password')], '密碼確認不一致'),
  fullName: yup
    .string()
    .required('姓名是必填項目')
    .min(2, '姓名至少需要 2 個字符')
    .max(100, '姓名最多 100 個字符'),
  phone: yup
    .string()
    .nullable()
    .matches(/^[+]?[\d\s\-\(\)]+$/, '請輸入有效的電話號碼'),
  timezone: yup.string().required('請選擇時區'),
  language: yup.string().required('請選擇語言'),
  acceptTerms: yup
    .boolean()
    .oneOf([true], '您必須同意服務條款和隱私政策'),
});

interface RegisterFormProps {
  onSubmit?: (data: RegisterFormData) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}

const RegisterForm: React.FC<RegisterFormProps> = ({
  onSubmit,
  isLoading = false,
  error,
  className = '',
}) => {
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);

  // Form setup
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    clearErrors,
    watch,
  } = useForm<RegisterFormData>({
    resolver: yupResolver(registerSchema),
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      fullName: '',
      phone: '',
      timezone: 'Asia/Taipei',
      language: 'zh-tw',
      acceptTerms: false,
    },
  });

  // Watch password for strength indicator
  const password = watch('password');

  // Handle form submission
  const handleFormSubmit = async (data: RegisterFormData) => {
    try {
      clearErrors();
      
      if (onSubmit) {
        await onSubmit(data);
      } else {
        // Default implementation
        console.log('Register attempt:', data);
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        toast.current?.show({
          severity: 'success',
          summary: '註冊成功',
          detail: '歡迎加入 PDLS！請查看您的電子郵件進行驗證。',
          life: 5000,
        });
        
        // Navigate to login or verification page
        navigate('/login?registered=true');
      }
    } catch (err: any) {
      console.error('Register error:', err);
      
      const errorMessage = err?.response?.data?.message || err?.message || '註冊失敗，請重試';
      
      toast.current?.show({
        severity: 'error',
        summary: '註冊失敗',
        detail: errorMessage,
        life: 5000,
      });
      
      // Handle specific validation errors
      if (err?.response?.status === 400 && err?.response?.data?.validation_errors) {
        err.response.data.validation_errors.forEach((validationError: any) => {
          setError(validationError.field as keyof RegisterFormData, {
            message: validationError.message,
          });
        });
      }
    }
  };

  // Show error toast if error prop changes
  React.useEffect(() => {
    if (error) {
      toast.current?.show({
        severity: 'error',
        summary: '註冊失敗',
        detail: error,
        life: 5000,
      });
    }
  }, [error]);

  // Helper function to get form error message
  const getFormErrorMessage = (name: keyof RegisterFormData) => {
    return errors[name] && (
      <small className="p-error block mt-1">
        {errors[name]?.message}
      </small>
    );
  };

  // Password strength indicator
  const getPasswordStrength = (password: string) => {
    if (!password) return null;
    
    let score = 0;
    if (password.length >= 8) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    
    const strength = ['很弱', '弱', '普通', '強', '很強'][score - 1];
    const color = ['#f44336', '#ff9800', '#ffeb3b', '#4caf50', '#2196f3'][score - 1];
    
    return { strength, color, score };
  };

  const passwordStrength = getPasswordStrength(password);

  return (
    <div className={`register-form-container ${className}`}>
      <Toast ref={toast} />
      
      <Card className="register-card shadow-3">
        <div className="register-header text-center mb-4">
          <div className="register-logo mb-3">
            <i className="pi pi-user-plus text-6xl text-primary"></i>
          </div>
          <h2 className="text-900 text-3xl font-medium mb-2">
            建立新帳戶
          </h2>
          <p className="text-600 text-lg mb-0">
            加入 PDLS 開始您的項目開發之旅
          </p>
        </div>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="register-form">
          {/* Username Field */}
          <div className="field mb-3">
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

          {/* Email Field */}
          <div className="field mb-3">
            <label htmlFor="email" className="block text-900 font-medium mb-2">
              電子郵件 *
            </label>
            <Controller
              name="email"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <InputText
                    id="email"
                    {...field}
                    type="email"
                    placeholder="請輸入電子郵件地址"
                    className={classNames(
                      'w-full p-3',
                      { 'p-invalid': fieldState.error }
                    )}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('email')}
                </>
              )}
            />
          </div>

          {/* Full Name Field */}
          <div className="field mb-3">
            <label htmlFor="fullName" className="block text-900 font-medium mb-2">
              姓名 *
            </label>
            <Controller
              name="fullName"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <InputText
                    id="fullName"
                    {...field}
                    placeholder="請輸入您的姓名"
                    className={classNames(
                      'w-full p-3',
                      { 'p-invalid': fieldState.error }
                    )}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('fullName')}
                </>
              )}
            />
          </div>

          {/* Phone Field */}
          <div className="field mb-3">
            <label htmlFor="phone" className="block text-900 font-medium mb-2">
              電話號碼
            </label>
            <Controller
              name="phone"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <InputText
                    id="phone"
                    {...field}
                    placeholder="請輸入電話號碼（選填）"
                    className={classNames(
                      'w-full p-3',
                      { 'p-invalid': fieldState.error }
                    )}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('phone')}
                </>
              )}
            />
          </div>

          {/* Password Field */}
          <div className="field mb-3">
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
                    promptLabel="輸入密碼"
                    weakLabel="弱"
                    mediumLabel="中等"
                    strongLabel="強"
                    disabled={isLoading || isSubmitting}
                  />
                  {passwordStrength && (
                    <div className="password-strength mt-2">
                      <div className="flex align-items-center">
                        <div 
                          className="password-strength-bar flex-1 mr-2" 
                          style={{ 
                            height: '4px', 
                            background: '#e9ecef',
                            borderRadius: '2px',
                            overflow: 'hidden'
                          }}
                        >
                          <div 
                            style={{
                              width: `${(passwordStrength.score / 5) * 100}%`,
                              height: '100%',
                              background: passwordStrength.color,
                              transition: 'all 0.3s ease'
                            }}
                          />
                        </div>
                        <span 
                          className="text-sm font-medium"
                          style={{ color: passwordStrength.color }}
                        >
                          {passwordStrength.strength}
                        </span>
                      </div>
                    </div>
                  )}
                  {getFormErrorMessage('password')}
                </>
              )}
            />
          </div>

          {/* Confirm Password Field */}
          <div className="field mb-3">
            <label htmlFor="confirmPassword" className="block text-900 font-medium mb-2">
              確認密碼 *
            </label>
            <Controller
              name="confirmPassword"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <Password
                    id="confirmPassword"
                    {...field}
                    placeholder="請再次輸入密碼"
                    className={classNames(
                      'w-full',
                      { 'p-invalid': fieldState.error }
                    )}
                    inputClassName="w-full p-3"
                    toggleMask
                    feedback={false}
                    disabled={isLoading || isSubmitting}
                  />
                  {getFormErrorMessage('confirmPassword')}
                </>
              )}
            />
          </div>

          {/* Timezone and Language Row */}
          <div className="formgrid grid mb-3">
            <div className="field col-12 md:col-6">
              <label htmlFor="timezone" className="block text-900 font-medium mb-2">
                時區 *
              </label>
              <Controller
                name="timezone"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <Dropdown
                      id="timezone"
                      {...field}
                      options={TIMEZONE_OPTIONS}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="選擇時區"
                      className={classNames(
                        'w-full',
                        { 'p-invalid': fieldState.error }
                      )}
                      disabled={isLoading || isSubmitting}
                    />
                    {getFormErrorMessage('timezone')}
                  </>
                )}
              />
            </div>
            <div className="field col-12 md:col-6">
              <label htmlFor="language" className="block text-900 font-medium mb-2">
                語言 *
              </label>
              <Controller
                name="language"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <Dropdown
                      id="language"
                      {...field}
                      options={LANGUAGE_OPTIONS}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="選擇語言"
                      className={classNames(
                        'w-full',
                        { 'p-invalid': fieldState.error }
                      )}
                      disabled={isLoading || isSubmitting}
                    />
                    {getFormErrorMessage('language')}
                  </>
                )}
              />
            </div>
          </div>

          {/* Terms and Conditions */}
          <div className="field mb-4">
            <Controller
              name="acceptTerms"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <div className="flex align-items-start">
                    <Checkbox
                      id="acceptTerms"
                      checked={field.value}
                      onChange={(e) => field.onChange(e.checked)}
                      disabled={isLoading || isSubmitting}
                      className={classNames(
                        'mr-2 mt-1',
                        { 'p-invalid': fieldState.error }
                      )}
                    />
                    <label htmlFor="acceptTerms" className="text-900 cursor-pointer text-sm">
                      我同意{' '}
                      <Link to="/terms" className="text-primary hover:text-primary-700 no-underline">
                        服務條款
                      </Link>
                      {' '}和{' '}
                      <Link to="/privacy" className="text-primary hover:text-primary-700 no-underline">
                        隱私政策
                      </Link>
                    </label>
                  </div>
                  {getFormErrorMessage('acceptTerms')}
                </>
              )}
            />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            label="建立帳戶"
            className="w-full p-3 text-xl font-bold"
            disabled={isLoading || isSubmitting}
            loading={isLoading || isSubmitting}
          />

          <Divider align="center" className="my-4">
            <span className="text-600 text-sm">或</span>
          </Divider>

          {/* Login Link */}
          <div className="text-center">
            <span className="text-600 text-sm mr-2">已經有帳戶？</span>
            <Link 
              to="/login"
              className="text-primary hover:text-primary-700 text-sm no-underline font-medium"
            >
              立即登入
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

export default RegisterForm;