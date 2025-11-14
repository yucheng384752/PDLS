/**
 * Project Files Component
 * Manages project file uploads, downloads, and organization
 */

import React, { useState, useRef } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { FileUpload, FileUploadHandlerEvent } from 'primereact/fileupload';
import { Tag } from 'primereact/tag';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Toolbar } from 'primereact/toolbar';
import { ProgressBar } from 'primereact/progressbar';
import { Skeleton } from 'primereact/skeleton';
import { InputText } from 'primereact/inputtext';
import { Dialog } from 'primereact/dialog';
import { 
  ProjectFile, 
  ProjectMemberRole
} from '../../types/project';
import { projectService } from '../../services/projectService';

interface ProjectFilesProps {
  projectId: number;
  files: ProjectFile[];
  userRole: ProjectMemberRole | null;
  loading: boolean;
  onRefresh: () => void;
  onFilesUpdate: (files: ProjectFile[]) => void;
}

interface UploadProgress {
  [fileName: string]: number;
}

const ProjectFiles: React.FC<ProjectFilesProps> = ({
  projectId,
  files,
  userRole,
  loading,
  onRefresh,
  onFilesUpdate
}) => {
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({});
  const [renameDialogVisible, setRenameDialogVisible] = useState(false);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [newFileName, setNewFileName] = useState('');

  // Check permissions
  const canUploadFiles = userRole && ['owner', 'admin', 'member'].includes(userRole);
  const canDeleteFiles = userRole && ['owner', 'admin'].includes(userRole);
  const canRenameFiles = userRole && ['owner', 'admin'].includes(userRole);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get file icon based on content type
  const getFileIcon = (contentType: string): string => {
    if (contentType.startsWith('image/')) return 'pi pi-image';
    if (contentType.startsWith('video/')) return 'pi pi-video';
    if (contentType.startsWith('audio/')) return 'pi pi-volume-up';
    if (contentType.includes('pdf')) return 'pi pi-file-pdf';
    if (contentType.includes('word')) return 'pi pi-file-word';
    if (contentType.includes('excel') || contentType.includes('spreadsheet')) return 'pi pi-file-excel';
    if (contentType.includes('text')) return 'pi pi-file';
    if (contentType.includes('zip') || contentType.includes('compressed')) return 'pi pi-folder';
    return 'pi pi-file';
  };

  // File name template
  const fileNameTemplate = (rowData: ProjectFile) => {
    return (
      <div className="p-d-flex p-ai-center p-gap-2">
        <i className={getFileIcon(rowData.content_type)} style={{ fontSize: '1.2rem' }} />
        <div>
          <div className="p-text-bold">{rowData.filename}</div>
          <small className="p-text-secondary">{rowData.original_filename}</small>
        </div>
      </div>
    );
  };

  // File size template
  const fileSizeTemplate = (rowData: ProjectFile) => {
    return (
      <Tag value={formatFileSize(rowData.file_size)} severity="info" />
    );
  };

  // Content type template
  const contentTypeTemplate = (rowData: ProjectFile) => {
    return <span className="p-text-secondary">{rowData.content_type}</span>;
  };

  // Upload date template
  const uploadDateTemplate = (rowData: ProjectFile) => {
    return new Date(rowData.created_at).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Uploader template
  const uploaderTemplate = (rowData: ProjectFile) => {
    return (
      <div className="p-d-flex p-ai-center p-gap-2">
        <i className="pi pi-user" />
        <span>{rowData.uploader?.full_name || rowData.uploader?.username || 'Unknown'}</span>
      </div>
    );
  };

  // Actions template
  const actionsTemplate = (rowData: ProjectFile) => {
    return (
      <div className="p-d-flex p-gap-2">
        <Button
          icon="pi pi-download"
          className="p-button-rounded p-button-outlined p-button-sm"
          tooltip="Download file"
          onClick={() => handleDownloadFile(rowData)}
        />
        {canRenameFiles && (
          <Button
            icon="pi pi-pencil"
            className="p-button-rounded p-button-outlined p-button-sm"
            tooltip="Rename file"
            onClick={() => handleRenameFile(rowData)}
          />
        )}
        {canDeleteFiles && (
          <Button
            icon="pi pi-trash"
            className="p-button-rounded p-button-danger p-button-outlined p-button-sm"
            tooltip="Delete file"
            onClick={() => handleDeleteFile(rowData)}
          />
        )}
      </div>
    );
  };

  // Handle file upload
  const handleFileUpload = async (event: FileUploadHandlerEvent) => {
    const files = event.files;
    if (!files || files.length === 0) return;

    setUploading(true);

    try {
      for (const file of files) {
        const uploadData = {
          file: file,
          project_id: projectId
        };

        // Track upload progress
        const onProgress = (progress: number) => {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: progress
          }));
        };

        await projectService.uploadFile(uploadData, onProgress);
        
        // Remove from progress tracking
        setUploadProgress(prev => {
          const { [file.name]: removed, ...rest } = prev;
          return rest;
        });
      }

      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `${files.length} file(s) uploaded successfully`
      });

      // Clear file upload component
      if (fileUploadRef.current) {
        fileUploadRef.current.clear();
      }

      // Refresh files list
      onRefresh();
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to upload files'
      });
    } finally {
      setUploading(false);
      setUploadProgress({});
    }
  };

  // Handle file download
  const handleDownloadFile = async (file: ProjectFile) => {
    try {
      const downloadUrl = await projectService.getFileDownloadUrl(projectId, file.id);
      
      // Create temporary link to trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = file.original_filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'File download started'
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to download file'
      });
    }
  };

  // Handle file rename
  const handleRenameFile = (file: ProjectFile) => {
    setSelectedFile(file);
    setNewFileName(file.filename);
    setRenameDialogVisible(true);
  };

  // Confirm file rename
  const confirmRenameFile = async () => {
    if (!selectedFile || !newFileName.trim()) return;

    try {
      await projectService.updateFile(projectId, selectedFile.id, {
        filename: newFileName.trim()
      });

      // Update local state
      const updatedFiles = files.map(f =>
        f.id === selectedFile.id ? { ...f, filename: newFileName.trim() } : f
      );
      onFilesUpdate(updatedFiles);

      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'File renamed successfully'
      });

      setRenameDialogVisible(false);
      setSelectedFile(null);
      setNewFileName('');
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to rename file'
      });
    }
  };

  // Handle file delete
  const handleDeleteFile = (file: ProjectFile) => {
    confirmDialog({
      message: `Are you sure you want to delete "${file.filename}"? This action cannot be undone.`,
      header: 'Delete File',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          await projectService.deleteFile(projectId, file.id);
          
          // Update local state
          const updatedFiles = files.filter(f => f.id !== file.id);
          onFilesUpdate(updatedFiles);
          
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'File deleted successfully'
          });
        } catch (error: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: error.response?.data?.message || 'Failed to delete file'
          });
        }
      }
    });
  };

  // Rename dialog footer
  const renameDialogFooter = (
    <div>
      <Button
        label="Cancel"
        icon="pi pi-times"
        className="p-button-text"
        onClick={() => setRenameDialogVisible(false)}
      />
      <Button
        label="Rename"
        icon="pi pi-check"
        onClick={confirmRenameFile}
        disabled={!newFileName.trim() || newFileName === selectedFile?.filename}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="project-files-loading">
        <Skeleton width="100%" height="3rem" className="p-mb-3" />
        <Skeleton width="100%" height="400px" />
      </div>
    );
  }

  return (
    <div className="project-files">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Files Header */}
      <Card>
        <Toolbar
          left={
            <div className="p-d-flex p-ai-center p-gap-3">
              <h3 className="p-m-0">Project Files</h3>
              <Tag value={`${files.length} files`} />
              <Tag 
                value={formatFileSize(files.reduce((total, file) => total + file.file_size, 0))} 
                severity="info" 
              />
            </div>
          }
          right={
            canUploadFiles && (
              <FileUpload
                ref={fileUploadRef}
                mode="advanced"
                multiple
                accept="*/*"
                maxFileSize={100000000} // 100MB
                customUpload
                uploadHandler={handleFileUpload}
                chooseLabel="Select Files"
                uploadLabel="Upload"
                cancelLabel="Cancel"
                disabled={uploading}
                auto={false}
              />
            )
          }
        />

        {/* Upload Progress */}
        {Object.keys(uploadProgress).length > 0 && (
          <div className="upload-progress p-mt-3">
            {Object.entries(uploadProgress).map(([fileName, progress]) => (
              <div key={fileName} className="p-mb-2">
                <div className="p-d-flex p-jc-between p-ai-center p-mb-1">
                  <small>{fileName}</small>
                  <small>{progress}%</small>
                </div>
                <ProgressBar value={progress} />
              </div>
            ))}
          </div>
        )}

        {/* Files Table */}
        <div className="p-mt-3">
          <DataTable
            value={files}
            responsiveLayout="scroll"
            emptyMessage="No files uploaded yet"
            rows={10}
            paginator={files.length > 10}
            sortField="created_at"
            sortOrder={-1}
          >
            <Column
              field="filename"
              header="File Name"
              body={fileNameTemplate}
              sortable
              style={{ minWidth: '300px' }}
            />
            <Column
              field="file_size"
              header="Size"
              body={fileSizeTemplate}
              sortable
              style={{ width: '120px' }}
            />
            <Column
              field="content_type"
              header="Type"
              body={contentTypeTemplate}
              style={{ width: '150px' }}
            />
            <Column
              field="uploader"
              header="Uploaded By"
              body={uploaderTemplate}
              style={{ width: '150px' }}
            />
            <Column
              field="created_at"
              header="Upload Date"
              body={uploadDateTemplate}
              sortable
              style={{ width: '150px' }}
            />
            <Column
              body={actionsTemplate}
              style={{ width: '150px' }}
              bodyClassName="p-text-center"
            />
          </DataTable>
        </div>
      </Card>

      {/* Rename File Dialog */}
      <Dialog
        header="Rename File"
        visible={renameDialogVisible}
        onHide={() => setRenameDialogVisible(false)}
        footer={renameDialogFooter}
        style={{ width: '400px' }}
        modal
      >
        <div className="p-fluid">
          <div className="p-field">
            <label htmlFor="newFileName" className="p-text-bold">New File Name</label>
            <InputText
              id="newFileName"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder="Enter new file name"
              className="p-mt-2"
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default ProjectFiles;