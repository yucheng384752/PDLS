/**
 * Project Detail Component
 * Main project detail view with tabs for overview, members, files, and settings
 */

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { Skeleton } from 'primereact/skeleton';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Toolbar } from 'primereact/toolbar';
import { Menu } from 'primereact/menu';
import { MenuItem } from 'primereact/menuitem';
import { 
  Project, 
  ProjectMember, 
  ProjectFile, 
  ProjectActivity, 
  ProjectMemberRole, 
  ProjectStatus,
  ProjectPriority 
} from '../../types/project';
import { projectService } from '../../services/projectService';

// Tab components
import ProjectOverview from './ProjectOverview';
import ProjectMembers from './ProjectMembers';
import ProjectFiles from './ProjectFiles';
import ProjectSettings from './ProjectSettings';

interface ProjectDetailProps {
  projectId?: string;
}

const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId: propProjectId }) => {
  const { projectId: paramProjectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);
  const menuRef = useRef<Menu>(null);
  
  // Use projectId from props or params
  const projectId = propProjectId || paramProjectId;
  
  // Component state
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [activity, setActivity] = useState<ProjectActivity[]>([]);
  const [loading, setLoading] = useState({
    project: true,
    members: false,
    files: false,
    activity: false
  });
  const [error, setError] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<ProjectMemberRole | null>(null);

  // Load project data
  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;
    
    setLoading(prev => ({ ...prev, project: true }));
    setError(null);
    
    try {
      const projectData = await projectService.getProject(parseInt(projectId, 10));
      setProject(projectData);
      
      // Determine user role in this project
      const currentUserId = parseInt(getCurrentUserId(), 10); // Implement this helper
      const userMember = projectData.members?.find(m => m.user_id === currentUserId);
      setUserRole(userMember?.role || null);
      
    } catch (err: any) {
      console.error('Failed to load project:', err);
      setError(err.response?.data?.message || 'Failed to load project');
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load project data'
      });
    } finally {
      setLoading(prev => ({ ...prev, project: false }));
    }
  };

  const loadMembers = async () => {
    if (!projectId) return;
    
    setLoading(prev => ({ ...prev, members: true }));
    try {
      const membersData = await projectService.getProjectMembers({ project_id: parseInt(projectId, 10) });
      setMembers(membersData.members);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(prev => ({ ...prev, members: false }));
    }
  };

  const loadFiles = async () => {
    if (!projectId) return;
    
    setLoading(prev => ({ ...prev, files: true }));
    try {
      const filesData = await projectService.getProjectFiles({ project_id: parseInt(projectId, 10) });
      setFiles(filesData.files);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setLoading(prev => ({ ...prev, files: false }));
    }
  };

  const loadActivity = async () => {
    if (!projectId) return;
    
    setLoading(prev => ({ ...prev, activity: true }));
    try {
      const activityData = await projectService.getProjectActivity(parseInt(projectId, 10));
      setActivity(activityData.activities);
    } catch (err) {
      console.error('Failed to load activity:', err);
    } finally {
      setLoading(prev => ({ ...prev, activity: false }));
    }
  };

  // Helper function to get current user ID (implement based on your auth system)
  const getCurrentUserId = (): string => {
    // TODO: Implement based on your authentication system
    return 'current-user-id';
  };

  // Project action handlers
  const handleEditProject = () => {
    navigate(`/projects/${projectId}/edit`);
  };

  const handleDeleteProject = () => {
    confirmDialog({
      message: `Are you sure you want to delete project "${project?.name}"? This action cannot be undone.`,
      header: 'Delete Project',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        if (!projectId) return;
        
        try {
          await projectService.deleteProject(parseInt(projectId, 10));
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'Project deleted successfully'
          });
          navigate('/projects');
        } catch (err: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: err.response?.data?.message || 'Failed to delete project'
          });
        }
      }
    });
  };

  const handleArchiveProject = async () => {
    if (!project || !projectId) return;
    
    try {
      await projectService.updateProject(parseInt(projectId, 10), { 
        status: ProjectStatus.ARCHIVED 
      });
      
      setProject(prev => prev ? { ...prev, status: ProjectStatus.ARCHIVED } : null);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Project archived successfully'
      });
    } catch (err: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: err.response?.data?.message || 'Failed to archive project'
      });
    }
  };

  // Tab change handler
  const handleTabChange = (e: any) => {
    const newIndex = e.index;
    setActiveTabIndex(newIndex);
    
    // Load data for the active tab
    switch (newIndex) {
      case 1: // Members tab
        if (members.length === 0 && !loading.members) {
          loadMembers();
        }
        break;
      case 2: // Files tab
        if (files.length === 0 && !loading.files) {
          loadFiles();
        }
        break;
      case 3: // Settings tab
        if (activity.length === 0 && !loading.activity) {
          loadActivity();
        }
        break;
    }
  };

  // Project status badge
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

  // Priority badge
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

  // Action menu items
  const actionMenuItems: MenuItem[] = [
    {
      label: 'Edit Project',
      icon: 'pi pi-pencil',
      command: handleEditProject,
      disabled: !userRole || !['owner', 'admin'].includes(userRole)
    },
    {
      separator: true
    },
    {
      label: 'Archive Project',
      icon: 'pi pi-archive',
      command: handleArchiveProject,
      disabled: !userRole || userRole !== 'owner' || project?.status === ProjectStatus.ARCHIVED
    },
    {
      label: 'Delete Project',
      icon: 'pi pi-trash',
      className: 'p-menuitem-danger',
      command: handleDeleteProject,
      disabled: !userRole || userRole !== 'owner'
    }
  ];

  // Render loading state
  if (loading.project) {
    return (
      <div className="project-detail-loading">
        <Card>
          <div className="p-mb-3">
            <Skeleton width="300px" height="2rem" className="p-mb-2" />
            <Skeleton width="100%" height="1rem" />
          </div>
          <div className="p-d-flex p-jc-between p-ai-center p-mb-3">
            <div className="p-d-flex p-ai-center p-gap-2">
              <Skeleton width="80px" height="1.5rem" borderRadius="16px" />
              <Skeleton width="80px" height="1.5rem" borderRadius="16px" />
            </div>
            <Skeleton width="120px" height="2.5rem" />
          </div>
          <Skeleton width="100%" height="300px" />
        </Card>
      </div>
    );
  }

  // Render error state
  if (error || !project) {
    return (
      <div className="project-detail-error">
        <Card>
          <div className="p-text-center p-py-6">
            <i className="pi pi-exclamation-triangle" style={{ fontSize: '3rem', color: 'var(--red-500)' }} />
            <h3 className="p-mt-3 p-mb-2">Project Not Found</h3>
            <p className="p-text-secondary p-mb-4">
              {error || 'The requested project could not be found or you do not have permission to view it.'}
            </p>
            <Button
              label="Back to Projects"
              icon="pi pi-arrow-left"
              onClick={() => navigate('/projects')}
            />
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="project-detail">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Project Header */}
      <Card className="project-header p-mb-4">
        <Toolbar
          left={
            <div className="project-header-info">
              <div className="p-d-flex p-ai-center p-gap-3 p-mb-2">
                <h1 className="p-m-0">{project.name}</h1>
                <Badge
                  value={project.status}
                  severity={getStatusSeverity(project.status)}
                />
                <Badge
                  value={project.priority}
                  severity={getPrioritySeverity(project.priority)}
                />
              </div>
              
              {project.description && (
                <p className="p-text-secondary p-mb-2">{project.description}</p>
              )}
              
              {project.tags && project.tags.length > 0 && (
                <div className="project-tags p-d-flex p-gap-1 p-flex-wrap">
                  {project.tags.map((tag, index) => (
                    <Tag key={index} value={tag} />
                  ))}
                </div>
              )}
            </div>
          }
          right={
            <div className="project-actions p-d-flex p-gap-2">
              <Button
                label="Back"
                icon="pi pi-arrow-left"
                className="p-button-outlined"
                onClick={() => navigate('/projects')}
              />
              
              {userRole && ['owner', 'admin'].includes(userRole) && (
                <>
                  <Button
                    label="Actions"
                    icon="pi pi-ellipsis-v"
                    className="p-button-outlined"
                    onClick={(e) => menuRef.current?.toggle(e)}
                  />
                  <Menu
                    ref={menuRef}
                    model={actionMenuItems}
                    popup
                  />
                </>
              )}
            </div>
          }
        />
      </Card>

      {/* Project Content Tabs */}
      <Card>
        <TabView
          activeIndex={activeTabIndex}
          onTabChange={handleTabChange}
        >
          <TabPanel header="Overview" leftIcon="pi pi-home">
            <ProjectOverview
              project={project}
              members={members}
              files={files}
              activity={activity}
              userRole={userRole}
              onRefresh={loadProjectData}
            />
          </TabPanel>

          <TabPanel header={`Members (${project.member_count || 0})`} leftIcon="pi pi-users">
            <ProjectMembers
              projectId={project.id}
              members={members}
              userRole={userRole}
              loading={loading.members}
              onRefresh={loadMembers}
              onMemberUpdate={(updatedMembers: ProjectMember[]) => setMembers(updatedMembers)}
            />
          </TabPanel>

          <TabPanel header={`Files (${project.file_count || 0})`} leftIcon="pi pi-folder">
            <ProjectFiles
              projectId={project.id}
              files={files}
              userRole={userRole}
              loading={loading.files}
              onRefresh={loadFiles}
              onFilesUpdate={(updatedFiles: ProjectFile[]) => setFiles(updatedFiles)}
            />
          </TabPanel>

          <TabPanel header="Settings" leftIcon="pi pi-cog">
            <ProjectSettings
              project={project}
              userRole={userRole}
              activity={activity}
              loading={loading.activity}
              onProjectUpdate={(updatedProject: Project) => setProject(updatedProject)}
              onRefresh={loadActivity}
            />
          </TabPanel>
        </TabView>
      </Card>
    </div>
  );
};

export default ProjectDetail;