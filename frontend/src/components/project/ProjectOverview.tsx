/**
 * Project Overview Component
 * Displays project overview information, statistics, and recent activity
 */

import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Avatar } from 'primereact/avatar';
import { Chip } from 'primereact/chip';
import { 
  Project, 
  ProjectMember, 
  ProjectFile, 
  ProjectActivity, 
  ProjectMemberRole,
  ProjectStatus,
  ProjectPriority
} from '../../types/project';

interface ProjectOverviewProps {
  project: Project;
  members: ProjectMember[];
  files: ProjectFile[];
  activity: ProjectActivity[];
  userRole: ProjectMemberRole | null;
  onRefresh: () => void;
}

const ProjectOverview: React.FC<ProjectOverviewProps> = ({
  project,
  members,
  activity
}) => {

  // Format date helper
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Status badge helper
  const getStatusSeverity = (status: ProjectStatus): "success" | "info" | "warning" | "danger" | undefined => {
    switch (status) {
      case ProjectStatus.ACTIVE:
        return 'success';
      case ProjectStatus.PLANNING:
        return 'info';
      case ProjectStatus.ON_HOLD:
        return 'warning';
      case ProjectStatus.COMPLETED:
        return 'success';
      case ProjectStatus.CANCELLED:
      case ProjectStatus.ARCHIVED:
        return 'danger';
      default:
        return 'info';
    }
  };

  // Priority badge helper
  const getPrioritySeverity = (priority: ProjectPriority): "success" | "info" | "warning" | "danger" | undefined => {
    switch (priority) {
      case ProjectPriority.LOW:
        return 'success';
      case ProjectPriority.MEDIUM:
        return 'info';
      case ProjectPriority.HIGH:
        return 'warning';
      case ProjectPriority.CRITICAL:
        return 'danger';
      default:
        return 'info';
    }
  };

  // Activity type template
  const activityTypeTemplate = (rowData: ProjectActivity) => {
    return <Chip label={rowData.activity_type.replace('_', ' ')} className="p-mr-2" />;
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
        <span>{rowData.user?.full_name || rowData.user?.username}</span>
      </div>
    );
  };

  // Member role template
  const memberRoleTemplate = (rowData: ProjectMember) => {
    let severity: "success" | "info" | "warning" | "danger" = 'info';
    switch (rowData.role) {
      case 'owner':
        severity = 'danger';
        break;
      case 'admin':
        severity = 'warning';
        break;
      case 'member':
        severity = 'success';
        break;
      case 'viewer':
        severity = 'info';
        break;
    }
    return <Badge value={rowData.role} severity={severity} />;
  };

  return (
    <div className="project-overview">
      {/* Project Summary Cards */}
      <div className="p-grid p-mb-4">
        <div className="p-col-12 p-md-3">
          <Card className="p-text-center">
            <i className="pi pi-users" style={{ fontSize: '2rem', color: 'var(--primary-color)' }} />
            <h4 className="p-mt-2 p-mb-1">{project.member_count || 0}</h4>
            <p className="p-text-secondary p-m-0">Members</p>
          </Card>
        </div>
        
        <div className="p-col-12 p-md-3">
          <Card className="p-text-center">
            <i className="pi pi-folder" style={{ fontSize: '2rem', color: 'var(--green-500)' }} />
            <h4 className="p-mt-2 p-mb-1">{project.file_count || 0}</h4>
            <p className="p-text-secondary p-m-0">Files</p>
          </Card>
        </div>
        
        <div className="p-col-12 p-md-3">
          <Card className="p-text-center">
            <i className="pi pi-calendar" style={{ fontSize: '2rem', color: 'var(--blue-500)' }} />
            <h4 className="p-mt-2 p-mb-1">
              {project.start_date ? formatDate(project.start_date) : 'N/A'}
            </h4>
            <p className="p-text-secondary p-m-0">Start Date</p>
          </Card>
        </div>
        
        <div className="p-col-12 p-md-3">
          <Card className="p-text-center">
            <i className="pi pi-flag" style={{ fontSize: '2rem', color: 'var(--orange-500)' }} />
            <h4 className="p-mt-2 p-mb-1">
              {project.end_date ? formatDate(project.end_date) : 'N/A'}
            </h4>
            <p className="p-text-secondary p-m-0">End Date</p>
          </Card>
        </div>
      </div>

      {/* Project Information */}
      <div className="p-grid p-mb-4">
        <div className="p-col-12 p-lg-8">
          <Card title="Project Information" className="p-h-full">
            <div className="project-info p-mb-3">
              <div className="p-mb-3">
                <strong>Description:</strong>
                <p className="p-mt-2">{project.description || 'No description provided.'}</p>
              </div>
              
              <div className="p-d-flex p-gap-4 p-mb-3">
                <div>
                  <strong>Status:</strong>
                  <div className="p-mt-1">
                    <Badge value={project.status} severity={getStatusSeverity(project.status)} />
                  </div>
                </div>
                
                <div>
                  <strong>Priority:</strong>
                  <div className="p-mt-1">
                    <Badge value={project.priority} severity={getPrioritySeverity(project.priority)} />
                  </div>
                </div>
                
                <div>
                  <strong>Type:</strong>
                  <div className="p-mt-1">
                    <Badge value={project.project_type} />
                  </div>
                </div>
              </div>

              {project.tags && project.tags.length > 0 && (
                <div className="p-mb-3">
                  <strong>Tags:</strong>
                  <div className="p-mt-2 p-d-flex p-gap-1 p-flex-wrap">
                    {project.tags.map((tag, index) => (
                      <Tag key={index} value={tag} />
                    ))}
                  </div>
                </div>
              )}

              {(project.repository_url || project.documentation_url) && (
                <div>
                  <strong>Links:</strong>
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
            </div>
          </Card>
        </div>

        <div className="p-col-12 p-lg-4">
          <Card title="Recent Members" className="p-h-full">
            {members.length > 0 ? (
              <div className="recent-members">
                {members.slice(0, 5).map((member) => (
                  <div key={member.id} className="member-item p-d-flex p-jc-between p-ai-center p-mb-3">
                    <div className="p-d-flex p-ai-center p-gap-2">
                      <Avatar 
                        label={member.user?.username?.charAt(0).toUpperCase()} 
                        shape="circle" 
                        style={{ width: '24px', height: '24px' }}
                      />
                      <div>
                        <div className="p-text-bold">{member.user?.full_name || member.user?.username}</div>
                        <small className="p-text-secondary">{member.user?.email}</small>
                      </div>
                    </div>
                    {memberRoleTemplate(member)}
                  </div>
                ))}
                {members.length > 5 && (
                  <p className="p-text-secondary p-text-center p-mt-3">
                    And {members.length - 5} more members...
                  </p>
                )}
              </div>
            ) : (
              <p className="p-text-secondary p-text-center">No members found.</p>
            )}
          </Card>
        </div>
      </div>

      {/* Recent Activity */}
      <Card title="Recent Activity">
        {activity.length > 0 ? (
          <DataTable
            value={activity.slice(0, 10)}
            responsiveLayout="scroll"
            size="small"
          >
            <Column 
              field="activity_type" 
              header="Type" 
              body={activityTypeTemplate}
              style={{ width: '150px' }}
            />
            <Column field="title" header="Activity" />
            <Column 
              field="user" 
              header="User" 
              body={activityUserTemplate}
              style={{ width: '200px' }}
            />
            <Column 
              field="timestamp" 
              header="Date" 
              body={(rowData) => formatDate(rowData.timestamp)}
              style={{ width: '120px' }}
            />
          </DataTable>
        ) : (
          <div className="p-text-center p-py-4">
            <i className="pi pi-clock" style={{ fontSize: '2rem', color: 'var(--text-color-secondary)' }} />
            <h4 className="p-mt-2">No Recent Activity</h4>
            <p className="p-text-secondary">Project activity will appear here as team members work on the project.</p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ProjectOverview;