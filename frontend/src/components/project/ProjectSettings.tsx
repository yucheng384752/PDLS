/**
 * Project Settings Component
 * Manages project configuration, settings, and activity history
 */

import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { TabView, TabPanel } from 'primereact/tabview';
import { Avatar } from 'primereact/avatar';
import { Tag } from 'primereact/tag';
import { Chip } from 'primereact/chip';
import { Skeleton } from 'primereact/skeleton';
import { 
  Project, 
  ProjectActivity, 
  ProjectMemberRole
} from '../../types/project';

interface ProjectSettingsProps {
  project: Project;
  userRole: ProjectMemberRole | null;
  activity: ProjectActivity[];
  loading: boolean;
  onProjectUpdate: (project: Project) => void;
  onRefresh: () => void;
}

const ProjectSettings: React.FC<ProjectSettingsProps> = ({
  project,
  userRole,
  activity,
  loading,
  onRefresh
}) => {
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Check permissions
  const canEditSettings = userRole && ['owner', 'admin'].includes(userRole);
  const isOwner = userRole === 'owner';

  // Format date helper
  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-TW', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Activity type template
  const activityTypeTemplate = (rowData: ProjectActivity) => {
    const getActivityColor = (type: string) => {
      switch (type) {
        case 'project_created': return 'success';
        case 'project_updated': return 'info';
        case 'member_added': return 'success';
        case 'member_removed': return 'warning';
        case 'file_uploaded': return 'info';
        case 'invitation_sent': return 'info';
        default: return 'secondary';
      }
    };

    return (
      <Chip 
        label={rowData.activity_type.replace(/_/g, ' ')} 
        className={`p-chip-${getActivityColor(rowData.activity_type)}`}
      />
    );
  };

  // Activity user template
  const activityUserTemplate = (rowData: ProjectActivity) => {
    return (
      <div className="p-d-flex p-ai-center p-gap-2">
        <Avatar
          label={rowData.user?.username?.charAt(0).toUpperCase()}
          shape="circle"
          style={{ width: '24px', height: '24px' }}
        />
        <span>{rowData.user?.full_name || rowData.user?.username || 'System'}</span>
      </div>
    );
  };

  // Project information section
  const renderProjectInfo = () => (
    <Card title="Project Information" className="p-mb-4">
      <div className="project-info-grid p-grid">
        <div className="p-col-12 p-md-6">
          <div className="info-item p-mb-3">
            <strong>Project Name:</strong>
            <p className="p-mt-1">{project.name}</p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>Description:</strong>
            <p className="p-mt-1">{project.description || 'No description provided'}</p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>Project Type:</strong>
            <p className="p-mt-1">
              <Tag value={project.project_type} />
            </p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>Status:</strong>
            <p className="p-mt-1">
              <Tag value={project.status} severity="info" />
            </p>
          </div>
        </div>
        
        <div className="p-col-12 p-md-6">
          <div className="info-item p-mb-3">
            <strong>Priority:</strong>
            <p className="p-mt-1">
              <Tag value={project.priority} severity="warning" />
            </p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>Start Date:</strong>
            <p className="p-mt-1">
              {project.start_date ? formatDateTime(project.start_date) : 'Not set'}
            </p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>End Date:</strong>
            <p className="p-mt-1">
              {project.end_date ? formatDateTime(project.end_date) : 'Not set'}
            </p>
          </div>
          
          <div className="info-item p-mb-3">
            <strong>Created:</strong>
            <p className="p-mt-1">{formatDateTime(project.created_at)}</p>
          </div>
        </div>
      </div>
      
      {project.tags && project.tags.length > 0 && (
        <div className="info-item p-mt-3">
          <strong>Tags:</strong>
          <div className="p-mt-2 p-d-flex p-gap-1 p-flex-wrap">
            {project.tags.map((tag, index) => (
              <Tag key={index} value={tag} />
            ))}
          </div>
        </div>
      )}
      
      {(project.repository_url || project.documentation_url) && (
        <div className="info-item p-mt-3">
          <strong>External Links:</strong>
          <div className="p-mt-2 p-d-flex p-gap-2">
            {project.repository_url && (
              <Button
                label="Repository"
                icon="pi pi-github"
                className="p-button-outlined p-button-sm"
                onClick={() => window.open(project.repository_url, '_blank')}
              />
            )}
            {project.documentation_url && (
              <Button
                label="Documentation"
                icon="pi pi-book"
                className="p-button-outlined p-button-sm"
                onClick={() => window.open(project.documentation_url, '_blank')}
              />
            )}
          </div>
        </div>
      )}
      
      {canEditSettings && (
        <div className="p-mt-4 p-d-flex p-gap-2">
          <Button
            label="Edit Project"
            icon="pi pi-pencil"
            className="p-button-outlined"
          />
          {isOwner && (
            <Button
              label="Advanced Settings"
              icon="pi pi-cog"
              className="p-button-outlined"
            />
          )}
        </div>
      )}
    </Card>
  );

  // Project statistics section
  const renderProjectStats = () => (
    <Card title="Project Statistics" className="p-mb-4">
      <div className="stats-grid p-grid">
        <div className="p-col-12 p-md-3">
          <div className="stat-item p-text-center">
            <i className="pi pi-users" style={{ fontSize: '2rem', color: 'var(--primary-color)' }} />
            <h4 className="p-mt-2 p-mb-1">{project.member_count || 0}</h4>
            <p className="p-text-secondary p-m-0">Members</p>
          </div>
        </div>
        
        <div className="p-col-12 p-md-3">
          <div className="stat-item p-text-center">
            <i className="pi pi-folder" style={{ fontSize: '2rem', color: 'var(--green-500)' }} />
            <h4 className="p-mt-2 p-mb-1">{project.file_count || 0}</h4>
            <p className="p-text-secondary p-m-0">Files</p>
          </div>
        </div>
        
        <div className="p-col-12 p-md-3">
          <div className="stat-item p-text-center">
            <i className="pi pi-clock" style={{ fontSize: '2rem', color: 'var(--blue-500)' }} />
            <h4 className="p-mt-2 p-mb-1">{activity.length}</h4>
            <p className="p-text-secondary p-m-0">Activities</p>
          </div>
        </div>
        
        <div className="p-col-12 p-md-3">
          <div className="stat-item p-text-center">
            <i className="pi pi-calendar" style={{ fontSize: '2rem', color: 'var(--orange-500)' }} />
            <h4 className="p-mt-2 p-mb-1">
              {project.updated_at ? new Date(project.updated_at).toLocaleDateString('zh-TW') : 'N/A'}
            </h4>
            <p className="p-text-secondary p-m-0">Last Updated</p>
          </div>
        </div>
      </div>
    </Card>
  );

  // Activity history section
  const renderActivityHistory = () => {
    if (loading) {
      return <Skeleton width="100%" height="400px" />;
    }

    return (
      <Card title="Activity History">
        <div className="p-d-flex p-jc-between p-ai-center p-mb-3">
          <p className="p-text-secondary">
            Recent project activity and changes
          </p>
          <Button
            label="Refresh"
            icon="pi pi-refresh"
            className="p-button-outlined p-button-sm"
            onClick={onRefresh}
          />
        </div>
        
        {activity.length > 0 ? (
          <DataTable
            value={activity}
            responsiveLayout="scroll"
            emptyMessage="No activity recorded yet"
            rows={15}
            paginator={activity.length > 15}
            sortField="timestamp"
            sortOrder={-1}
          >
            <Column
              field="activity_type"
              header="Type"
              body={activityTypeTemplate}
              style={{ width: '150px' }}
            />
            <Column field="title" header="Activity" style={{ minWidth: '250px' }} />
            <Column field="description" header="Description" style={{ minWidth: '200px' }} />
            <Column
              field="user"
              header="User"
              body={activityUserTemplate}
              style={{ width: '150px' }}
            />
            <Column
              field="timestamp"
              header="Date & Time"
              body={(rowData) => formatDateTime(rowData.timestamp)}
              style={{ width: '150px' }}
            />
          </DataTable>
        ) : (
          <div className="p-text-center p-py-6">
            <i className="pi pi-clock" style={{ fontSize: '3rem', color: 'var(--text-color-secondary)' }} />
            <h4 className="p-mt-3 p-mb-2">No Activity Yet</h4>
            <p className="p-text-secondary">
              Project activity will appear here as team members work on the project.
            </p>
          </div>
        )}
      </Card>
    );
  };

  // Danger zone section (owner only)
  const renderDangerZone = () => {
    if (!isOwner) return null;

    return (
      <Card title="Danger Zone" className="p-mt-4" style={{ borderColor: 'var(--red-500)' }}>
        <div className="danger-zone">
          <div className="p-d-flex p-jc-between p-ai-center p-mb-3">
            <div>
              <h5 className="p-m-0 p-text-bold" style={{ color: 'var(--red-500)' }}>
                Archive Project
              </h5>
              <p className="p-text-secondary p-mt-1 p-mb-0">
                Archive this project to hide it from active projects list
              </p>
            </div>
            <Button
              label="Archive"
              icon="pi pi-archive"
              className="p-button-outlined p-button-warning"
            />
          </div>
          
          <hr className="p-my-3" />
          
          <div className="p-d-flex p-jc-between p-ai-center">
            <div>
              <h5 className="p-m-0 p-text-bold" style={{ color: 'var(--red-500)' }}>
                Delete Project
              </h5>
              <p className="p-text-secondary p-mt-1 p-mb-0">
                Permanently delete this project and all its data
              </p>
            </div>
            <Button
              label="Delete"
              icon="pi pi-trash"
              className="p-button-outlined p-button-danger"
            />
          </div>
        </div>
      </Card>
    );
  };

  return (
    <div className="project-settings">
      <TabView 
        activeIndex={activeTabIndex} 
        onTabChange={(e) => setActiveTabIndex(e.index)}
      >
        <TabPanel header="General" leftIcon="pi pi-info-circle">
          <div className="general-settings">
            {renderProjectInfo()}
            {renderProjectStats()}
          </div>
        </TabPanel>

        <TabPanel header="Activity" leftIcon="pi pi-clock">
          <div className="activity-settings">
            {renderActivityHistory()}
          </div>
        </TabPanel>

        {isOwner && (
          <TabPanel header="Advanced" leftIcon="pi pi-exclamation-triangle">
            <div className="advanced-settings">
              <h3>Advanced Settings</h3>
              <p className="p-text-secondary p-mb-4">
                Advanced project management options. Use with caution.
              </p>
              {renderDangerZone()}
            </div>
          </TabPanel>
        )}
      </TabView>
    </div>
  );
};

export default ProjectSettings;