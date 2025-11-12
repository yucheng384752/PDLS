import React, { useState, useRef, useEffect } from 'react';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Button } from 'primereact/button';
import { Toast } from 'primereact/toast';
import { Divider } from 'primereact/divider';
import { Password } from 'primereact/password';
import { Checkbox } from 'primereact/checkbox';
import { Calendar } from 'primereact/calendar';
import { InputTextarea } from 'primereact/inputtextarea';
import { Skeleton } from 'primereact/skeleton';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { AvatarUpload } from './AvatarUpload';
import { UserService } from '../../services/userService';
import { useAuthStore } from '../../stores/authStore';
import { UserRole, UserProfile, UpdateUserProfile, ChangePassword } from '../../types/user';
import './UserProfile.css';

// Validation schemas
const profileSchema = yup.object().shape({
  username: yup.string()
    .required('用戶名稱為必填項目')
    .min(3, '用戶名稱至少需要3個字符')
    .max(50, '用戶名稱不能超過50個字符'),
  email: yup.string()
    .required('電子郵件為必填項目')
    .email('請輸入有效的電子郵件地址'),
  full_name: yup.string()
    .required('全名為必填項目')
    .max(100, '全名不能超過100個字符'),
  phone: yup.string()
    .nullable()
    .matches(/^[+]?[(]?[\d\s\-()]{10,20}$/, '請輸入有效的電話號碼'),
  timezone: yup.string().required('時區為必填項目'),
  language: yup.string().required('語言為必填項目'),
  bio: yup.string().nullable().max(500, '個人簡介不能超過500個字符'),
  birth_date: yup.date().nullable(),
  receive_notifications: yup.boolean(),
  is_public_profile: yup.boolean()
});

const passwordSchema = yup.object().shape({
  current_password: yup.string().required('請輸入目前的密碼'),
  new_password: yup.string()
    .required('請輸入新密碼')
    .min(8, '密碼至少需要8個字符')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
      '密碼必須包含大小寫字母、數字和特殊字符'
    ),
  confirm_password: yup.string()
    .required('請確認新密碼')
    .oneOf([yup.ref('new_password')], '密碼確認不一致')
});

interface UserProfileProps {
  userId?: string;
  viewMode?: boolean;
}

export const UserProfile: React.FC<UserProfileProps> = ({ 
  userId, 
  viewMode = false 
}) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  
  const toast = useRef<Toast>(null);
  const { user: currentUser } = useAuthStore();
  const userService = new UserService();

  // Check if current user can edit this profile
  const canEdit = !viewMode && (!userId || userId === currentUser?.id);

  // Form for profile data
  const profileForm = useForm<UpdateUserProfile>({
    resolver: yupResolver(profileSchema),
    mode: 'onChange'
  });

  // Form for password change
  const passwordForm = useForm<ChangePassword>({
    resolver: yupResolver(passwordSchema),
    mode: 'onChange'
  });

  const timezones = [
    { label: 'UTC+8 (台北)', value: 'Asia/Taipei' },
    { label: 'UTC+0 (倫敦)', value: 'Europe/London' },
    { label: 'UTC-5 (紐約)', value: 'America/New_York' },
    { label: 'UTC-8 (洛杉磯)', value: 'America/Los_Angeles' },
    { label: 'UTC+9 (東京)', value: 'Asia/Tokyo' },
  ];

  const languages = [
    { label: '繁體中文', value: 'zh-TW' },
    { label: 'English', value: 'en-US' },
    { label: '简体中文', value: 'zh-CN' },
    { label: '日本語', value: 'ja-JP' },
  ];

  useEffect(() => {
    loadUserProfile();
  }, [userId]);

  const loadUserProfile = async () => {
    try {
      setLoading(true);
      const targetUserId = userId || currentUser?.id;
      
      if (!targetUserId) {
        throw new Error('無法取得用戶ID');
      }

      const profile = await userService.getUserProfile(targetUserId);
      setUserProfile(profile);
      
      // Set form default values
      profileForm.reset({
        username: profile.username,
        email: profile.email,
        full_name: profile.full_name,
        phone: profile.phone || '',
        timezone: profile.timezone,
        language: profile.language,
        bio: profile.bio || '',
        birth_date: profile.birth_date ? new Date(profile.birth_date) : null,
        receive_notifications: profile.receive_notifications,
        is_public_profile: profile.is_public_profile
      });

    } catch (error) {
      console.error('Load user profile error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '載入失敗',
        detail: '無法載入用戶資料',
        life: 5000
      });
    } finally {
      setLoading(false);
    }
  };

  const onSubmitProfile = async (data: UpdateUserProfile) => {
    try {
      setSaving(true);
      const targetUserId = userId || currentUser?.id;
      
      if (!targetUserId) {
        throw new Error('無法取得用戶ID');
      }

      await userService.updateUserProfile(targetUserId, data);
      
      toast.current?.show({
        severity: 'success',
        summary: '更新成功',
        detail: '用戶資料已更新',
        life: 3000
      });

      // Reload profile data
      await loadUserProfile();

    } catch (error) {
      console.error('Update profile error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '更新失敗',
        detail: error instanceof Error ? error.message : '請稍後重試',
        life: 5000
      });
    } finally {
      setSaving(false);
    }
  };

  const onSubmitPassword = async (data: ChangePassword) => {
    try {
      setChangingPassword(true);
      
      await userService.changePassword(data);
      
      toast.current?.show({
        severity: 'success',
        summary: '密碼已更新',
        detail: '密碼變更成功',
        life: 3000
      });

      // Reset password form and hide section
      passwordForm.reset();
      setShowPasswordChange(false);

    } catch (error) {
      console.error('Change password error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '密碼變更失敗',
        detail: error instanceof Error ? error.message : '請稍後重試',
        life: 5000
      });
    } finally {
      setChangingPassword(false);
    }
  };

  const onAvatarChange = (avatarUrl: string) => {
    if (userProfile) {
      setUserProfile({ ...userProfile, avatar_url: avatarUrl });
    }
  };

  if (loading) {
    return (
      <div className="user-profile-container">
        <Card className="profile-card">
          <div className="profile-header text-center mb-4">
            <Skeleton shape="circle" size="6rem" className="mx-auto mb-3" />
            <Skeleton width="200px" height="2rem" className="mx-auto mb-2" />
            <Skeleton width="150px" height="1rem" className="mx-auto" />
          </div>
          <Divider />
          <div className="profile-form">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="field mb-3">
                <Skeleton width="100px" height="1rem" className="mb-2" />
                <Skeleton width="100%" height="2.5rem" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (!userProfile) {
    return (
      <div className="user-profile-container">
        <Card className="profile-card text-center">
          <i className="pi pi-user-x text-6xl text-gray-400 mb-3"></i>
          <h3>找不到用戶</h3>
          <p className="text-gray-600">請檢查用戶ID是否正確</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="user-profile-container">
      <Toast ref={toast} />
      
      <Card className="profile-card">
        {/* Profile Header */}
        <div className="profile-header text-center mb-4">
          <AvatarUpload
            currentAvatar={userProfile.avatar_url}
            onAvatarChange={onAvatarChange}
            size="xlarge"
            disabled={!canEdit}
          />
          
          <h2 className="profile-name mt-3 mb-1">
            {userProfile.full_name}
          </h2>
          
          <div className="profile-meta">
            <span className="profile-username">@{userProfile.username}</span>
            <span className="profile-role">
              <i className="pi pi-shield mr-1"></i>
              {userProfile.role}
            </span>
          </div>
          
          {userProfile.bio && (
            <p className="profile-bio mt-3 text-gray-600">
              {userProfile.bio}
            </p>
          )}
        </div>

        <Divider />

        {/* Profile Form */}
        <form onSubmit={profileForm.handleSubmit(onSubmitProfile)} className="profile-form">
          <div className="formgrid grid">
            {/* Basic Information */}
            <div className="col-12">
              <h4>基本資訊</h4>
            </div>
            
            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="username">用戶名稱</label>
                <Controller
                  name="username"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <InputText
                        id="username"
                        {...field}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="email">電子郵件</label>
                <Controller
                  name="email"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <InputText
                        id="email"
                        {...field}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12">
              <div className="field">
                <label htmlFor="full_name">全名</label>
                <Controller
                  name="full_name"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <InputText
                        id="full_name"
                        {...field}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="phone">電話號碼</label>
                <Controller
                  name="phone"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <InputText
                        id="phone"
                        {...field}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="birth_date">出生日期</label>
                <Controller
                  name="birth_date"
                  control={profileForm.control}
                  render={({ field }) => (
                    <Calendar
                      id="birth_date"
                      value={field.value}
                      onChange={(e) => field.onChange(e.value)}
                      disabled={!canEdit}
                      showIcon
                      dateFormat="yy/mm/dd"
                      yearNavigator
                      yearRange="1950:2020"
                    />
                  )}
                />
              </div>
            </div>

            {/* Preferences */}
            <div className="col-12">
              <Divider />
              <h4>偏好設定</h4>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="timezone">時區</label>
                <Controller
                  name="timezone"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <Dropdown
                        id="timezone"
                        {...field}
                        options={timezones}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="language">語言</label>
                <Controller
                  name="language"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <Dropdown
                        id="language"
                        {...field}
                        options={languages}
                        disabled={!canEdit}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12">
              <div className="field">
                <label htmlFor="bio">個人簡介</label>
                <Controller
                  name="bio"
                  control={profileForm.control}
                  render={({ field, fieldState }) => (
                    <>
                      <InputTextarea
                        id="bio"
                        {...field}
                        disabled={!canEdit}
                        rows={4}
                        className={fieldState.error ? 'p-invalid' : ''}
                      />
                      {fieldState.error && (
                        <small className="p-error">{fieldState.error.message}</small>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            {/* Privacy Settings */}
            <div className="col-12">
              <Divider />
              <h4>隱私設定</h4>
            </div>

            <div className="col-12">
              <div className="field-checkbox">
                <Controller
                  name="receive_notifications"
                  control={profileForm.control}
                  render={({ field }) => (
                    <>
                      <Checkbox
                        inputId="receive_notifications"
                        checked={field.value}
                        onChange={(e) => field.onChange(e.checked)}
                        disabled={!canEdit}
                      />
                      <label htmlFor="receive_notifications" className="ml-2">
                        接收系統通知
                      </label>
                    </>
                  )}
                />
              </div>
            </div>

            <div className="col-12">
              <div className="field-checkbox">
                <Controller
                  name="is_public_profile"
                  control={profileForm.control}
                  render={({ field }) => (
                    <>
                      <Checkbox
                        inputId="is_public_profile"
                        checked={field.value}
                        onChange={(e) => field.onChange(e.checked)}
                        disabled={!canEdit}
                      />
                      <label htmlFor="is_public_profile" className="ml-2">
                        公開個人資料
                      </label>
                    </>
                  )}
                />
              </div>
            </div>

            {/* Action Buttons */}
            {canEdit && (
              <div className="col-12">
                <Divider />
                <div className="flex justify-content-between">
                  <Button
                    label="變更密碼"
                    icon="pi pi-key"
                    className="p-button-outlined"
                    onClick={() => setShowPasswordChange(!showPasswordChange)}
                  />
                  
                  <Button
                    type="submit"
                    label="儲存變更"
                    icon="pi pi-save"
                    loading={saving}
                    disabled={!profileForm.formState.isValid}
                  />
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Password Change Section */}
        {canEdit && showPasswordChange && (
          <>
            <Divider />
            <div className="password-change-section">
              <h4>變更密碼</h4>
              
              <form onSubmit={passwordForm.handleSubmit(onSubmitPassword)}>
                <div className="formgrid grid">
                  <div className="col-12">
                    <div className="field">
                      <label htmlFor="current_password">目前密碼</label>
                      <Controller
                        name="current_password"
                        control={passwordForm.control}
                        render={({ field, fieldState }) => (
                          <>
                            <Password
                              id="current_password"
                              {...field}
                              feedback={false}
                              className={fieldState.error ? 'p-invalid' : ''}
                            />
                            {fieldState.error && (
                              <small className="p-error">{fieldState.error.message}</small>
                            )}
                          </>
                        )}
                      />
                    </div>
                  </div>

                  <div className="col-12 md:col-6">
                    <div className="field">
                      <label htmlFor="new_password">新密碼</label>
                      <Controller
                        name="new_password"
                        control={passwordForm.control}
                        render={({ field, fieldState }) => (
                          <>
                            <Password
                              id="new_password"
                              {...field}
                              promptLabel="輸入密碼"
                              weakLabel="弱"
                              mediumLabel="中等"
                              strongLabel="強"
                              className={fieldState.error ? 'p-invalid' : ''}
                            />
                            {fieldState.error && (
                              <small className="p-error">{fieldState.error.message}</small>
                            )}
                          </>
                        )}
                      />
                    </div>
                  </div>

                  <div className="col-12 md:col-6">
                    <div className="field">
                      <label htmlFor="confirm_password">確認新密碼</label>
                      <Controller
                        name="confirm_password"
                        control={passwordForm.control}
                        render={({ field, fieldState }) => (
                          <>
                            <Password
                              id="confirm_password"
                              {...field}
                              feedback={false}
                              className={fieldState.error ? 'p-invalid' : ''}
                            />
                            {fieldState.error && (
                              <small className="p-error">{fieldState.error.message}</small>
                            )}
                          </>
                        )}
                      />
                    </div>
                  </div>

                  <div className="col-12">
                    <div className="flex justify-content-end gap-2">
                      <Button
                        label="取消"
                        icon="pi pi-times"
                        className="p-button-text"
                        onClick={() => {
                          setShowPasswordChange(false);
                          passwordForm.reset();
                        }}
                      />
                      
                      <Button
                        type="submit"
                        label="變更密碼"
                        icon="pi pi-check"
                        loading={changingPassword}
                        disabled={!passwordForm.formState.isValid}
                      />
                    </div>
                  </div>
                </div>
              </form>
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

export default UserProfile;