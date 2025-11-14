/**
 * Project Create Page Component
 * Page for creating new projects using the ProjectForm component
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Toast } from 'primereact/toast';
import { Button } from 'primereact/button';
import ProjectForm from '../components/project/ProjectForm';
import { CreateProjectRequest, UpdateProjectRequest, ProjectType } from '../types/project';
import { projectService } from '../services/projectService';

const ProjectCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = React.useState(false);
  const toast = React.useRef<Toast>(null);

  const handleCreateProject = async (data: CreateProjectRequest | UpdateProjectRequest) => {
    setLoading(true);
    try {
      // Type guard to ensure we have all required fields for creation
      if (!data.name) {
        throw new Error('Project name is required');
      }
      
      const createData: CreateProjectRequest = {
        name: data.name,
        description: data.description,
        project_type: data.project_type || ProjectType.SOFTWARE,
        start_date: data.start_date,
        end_date: data.end_date,
        status: data.status,
        priority: data.priority,
        tags: data.tags || [],
        repository_url: data.repository_url,
        documentation_url: data.documentation_url
      };
      
      const newProject = await projectService.createProject(createData);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Project created successfully'
      });
      
      // Navigate to project detail page after creation
      setTimeout(() => {
        navigate(`/projects/${newProject.id}`);
      }, 1500);
      
    } catch (error: any) {
      console.error('Failed to create project:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to create project'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    navigate('/projects');
  };

  return (
    <div className="project-create-page">
      <Toast ref={toast} />
      
      {/* Page Header */}
      <div className="page-header p-mb-4">
        <div className="p-d-flex p-jc-between p-ai-center">
          <div>
            <h1 className="p-text-bold p-mb-2">Create New Project</h1>
            <p className="p-text-secondary">
              Set up a new project with all the necessary information and configuration.
            </p>
          </div>
          
          <Button
            label="Back to Projects"
            icon="pi pi-arrow-left"
            className="p-button-outlined"
            onClick={() => navigate('/projects')}
          />
        </div>
      </div>

      {/* Project Form */}
      <div className="project-form-container">
        <ProjectForm
          onSubmit={handleCreateProject}
          onCancel={handleCancel}
          loading={loading}
        />
      </div>
    </div>
  );
};

export default ProjectCreatePage;