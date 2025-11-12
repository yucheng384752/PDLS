import React, { useRef, useState } from 'react';
import { FileUpload, FileUploadUploadEvent } from 'primereact/fileupload';
import { Avatar } from 'primereact/avatar';
import { Button } from 'primereact/button';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { ProgressBar } from 'primereact/progressbar';
import { Divider } from 'primereact/divider';
import { classNames } from 'primereact/utils';
import './AvatarUpload.css';

interface AvatarUploadProps {
  currentAvatar?: string;
  onAvatarChange: (avatarUrl: string) => void;
  size?: 'small' | 'medium' | 'large' | 'xlarge';
  disabled?: boolean;
  className?: string;
}

export const AvatarUpload: React.FC<AvatarUploadProps> = ({
  currentAvatar,
  onAvatarChange,
  size = 'large',
  disabled = false,
  className
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewImage, setPreviewImage] = useState<string>('');
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  const maxFileSize = 5 * 1024 * 1024; // 5MB
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

  const onUpload = async (event: FileUploadUploadEvent) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      const file = event.files[0];
      
      // Validate file size
      if (file.size > maxFileSize) {
        toast.current?.show({
          severity: 'error',
          summary: '檔案太大',
          detail: '頭像檔案大小不能超過 5MB',
          life: 5000
        });
        return;
      }

      // Validate file type
      if (!allowedTypes.includes(file.type)) {
        toast.current?.show({
          severity: 'error',
          summary: '檔案格式不支援',
          detail: '請上傳 JPEG、PNG、GIF 或 WebP 格式的圖片',
          life: 5000
        });
        return;
      }

      // Create form data
      const formData = new FormData();
      formData.append('avatar', file);

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Make API call to upload avatar
      const response = await fetch('/api/v1/users/avatar', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上傳失敗');
      }

      const result = await response.json();
      
      // Update avatar URL
      onAvatarChange(result.avatar_url);

      toast.current?.show({
        severity: 'success',
        summary: '上傳成功',
        detail: '頭像已更新',
        life: 3000
      });

      // Clear file input
      if (fileUploadRef.current) {
        fileUploadRef.current.clear();
      }

    } catch (error) {
      console.error('Avatar upload error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '上傳失敗',
        detail: error instanceof Error ? error.message : '請稍後重試',
        life: 5000
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const onSelect = (event: any) => {
    const file = event.files[0];
    if (file) {
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewImage(e.target?.result as string);
        setPreviewVisible(true);
      };
      reader.readAsDataURL(file);
    }
  };

  const onError = (event: any) => {
    console.error('File upload error:', event);
    toast.current?.show({
      severity: 'error',
      summary: '上傳錯誤',
      detail: '檔案上傳時發生錯誤',
      life: 5000
    });
  };

  const removeAvatar = async () => {
    try {
      const response = await fetch('/api/v1/users/avatar', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '刪除失敗');
      }

      onAvatarChange('');
      
      toast.current?.show({
        severity: 'success',
        summary: '刪除成功',
        detail: '頭像已移除',
        life: 3000
      });
    } catch (error) {
      console.error('Remove avatar error:', error);
      toast.current?.show({
        severity: 'error',
        summary: '刪除失敗',
        detail: error instanceof Error ? error.message : '請稍後重試',
        life: 5000
      });
    }
  };

  const getAvatarSize = () => {
    switch (size) {
      case 'small': return '48px';
      case 'medium': return '64px';
      case 'large': return '96px';
      case 'xlarge': return '128px';
      default: return '96px';
    }
  };

  return (
    <div className={classNames('avatar-upload-container', className)}>
      <Toast ref={toast} />
      
      <div className="avatar-preview-section">
        <div className="avatar-wrapper" style={{ '--avatar-size': getAvatarSize() } as React.CSSProperties}>
          {currentAvatar ? (
            <Avatar
              image={currentAvatar}
              size={size}
              shape="circle"
              className="avatar-image cursor-pointer"
              onClick={() => {
                setPreviewImage(currentAvatar);
                setPreviewVisible(true);
              }}
            />
          ) : (
            <Avatar
              icon="pi pi-user"
              size={size}
              shape="circle"
              className="avatar-placeholder"
            />
          )}
          
          {!disabled && (
            <div className="avatar-overlay">
              <Button
                icon="pi pi-camera"
                className="p-button-rounded p-button-secondary avatar-edit-btn"
                onClick={() => fileUploadRef.current?.choose()}
                tooltip="更換頭像"
                tooltipOptions={{ position: 'top' }}
              />
            </div>
          )}
        </div>

        {uploading && (
          <div className="upload-progress mt-3">
            <ProgressBar 
              value={uploadProgress} 
              displayValueTemplate={`${uploadProgress}%`}
              className="progress-bar-custom"
            />
            <small className="text-muted mt-1 block">正在上傳頭像...</small>
          </div>
        )}
      </div>

      {!disabled && (
        <div className="avatar-actions mt-3">
          <FileUpload
            ref={fileUploadRef}
            mode="basic"
            name="avatar"
            url="/api/v1/users/avatar"
            accept="image/*"
            maxFileSize={maxFileSize}
            onUpload={onUpload}
            onSelect={onSelect}
            onError={onError}
            auto={false}
            chooseLabel="選擇頭像"
            className="upload-button"
            disabled={uploading}
            customUpload={true}
          />

          {currentAvatar && (
            <>
              <Divider layout="vertical" />
              <Button
                label="移除頭像"
                icon="pi pi-trash"
                className="p-button-outlined p-button-danger"
                onClick={removeAvatar}
                disabled={uploading}
              />
            </>
          )}
        </div>
      )}

      <Dialog
        visible={previewVisible}
        style={{ width: '50vw', minWidth: '400px' }}
        header="頭像預覽"
        modal
        onHide={() => setPreviewVisible(false)}
        draggable={false}
        resizable={false}
      >
        <div className="text-center">
          <img
            src={previewImage}
            alt="頭像預覽"
            style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px' }}
          />
        </div>
      </Dialog>

      <div className="upload-info mt-3">
        <small className="text-muted">
          <i className="pi pi-info-circle mr-1"></i>
          支援 JPEG、PNG、GIF、WebP 格式，檔案大小不超過 5MB
        </small>
      </div>
    </div>
  );
};

export default AvatarUpload;