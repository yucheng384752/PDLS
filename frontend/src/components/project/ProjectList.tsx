/**
 * Project List Component
 * Main component for displaying and managing projects with search, filtering, and actions
 */

import React, { useState, useEffect, useCallback } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Tag } from 'primereact/tag';
import { Card } from 'primereact/card';
import { Toolbar } from 'primereact/toolbar';
import { Badge } from 'primereact/badge';
import { Avatar } from 'primereact/avatar';
import { ProgressBar } from 'primereact/progressbar';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { confirmDialog } from 'primereact/confirmdialog';
import { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
// import toast from 'react-hot-toast';

import { projectService } from '../../services/projectService';
import {
  Project,
  ProjectType,
  ProjectStatus,
  ProjectPriority,
  ProjectListQuery,
  ProjectListState
} from '../../types/project';

interface ProjectListProps {
  onProjectSelect?: (project: Project) => void;
  showActions?: boolean;
  compact?: boolean;
  embedded?: boolean;
}

const ProjectList: React.FC<ProjectListProps> = ({
  onProjectSelect,
  showActions = true,
  compact = false,
  embedded = false
}) => {
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);

  const [state, setState] = useState<ProjectListState>({
    projects: [],
    loading: false,
    query: {
      page: 1,
      page_size: 10,
      sort_by: 'created_at',
      sort_order: 'desc'
    },
    total: 0,
    selectedProjects: []
  });

  const [globalFilterValue, setGlobalFilterValue] = useState('');

  // Load projects
  const loadProjects = useCallback(async (query: ProjectListQuery = state.query) => {
    setState(prev => ({ ...prev, loading: true, error: undefined }));

    try {
      const result = await projectService.getProjects(query);
      setState(prev => ({
        ...prev,
        projects: result.projects,
        total: result.total,
        query,
        loading: false
      }));
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error.message || 'Failed to load projects'
      }));
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load projects'
      });
    }
  }, [state.query]);

  // Initial load
  useEffect(() => {
    loadProjects();
  }, []);

  // Handle search
  const onGlobalFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setGlobalFilterValue(value);
    
    const newQuery = {
      ...state.query,
      search: value || undefined,
      page: 1
    };

    setState(prev => ({ ...prev, query: newQuery }));
    
    // Debounced search
    const timeoutId = setTimeout(() => {
      loadProjects(newQuery);
    }, 500);

    return () => clearTimeout(timeoutId);
  };

  // Handle filter changes
  const onFilterChange = (field: keyof ProjectListQuery, value: any) => {
    const newQuery = {
      ...state.query,
      [field]: value,
      page: 1
    };

    setState(prev => ({ ...prev, query: newQuery }));
    loadProjects(newQuery);
  };

  // Handle pagination
  const onPageChange = (event: any) => {
    const newQuery = {
      ...state.query,
      page: event.page + 1,
      page_size: event.rows
    };

    setState(prev => ({ ...prev, query: newQuery }));
    loadProjects(newQuery);
  };

  // Handle sorting
  const onSort = (event: any) => {
    const newQuery: ProjectListQuery = {
      ...state.query,
      sort_by: event.sortField,
      sort_order: (event.sortOrder === 1 ? 'asc' : 'desc') as 'asc' | 'desc',
      page: 1
    };

    setState(prev => ({ ...prev, query: newQuery }));
    loadProjects(newQuery);
  };

  // Project actions
  const handleViewProject = (project: Project) => {
    if (onProjectSelect) {
      onProjectSelect(project);
    } else {
      navigate(`/projects/${project.id}`);
    }
  };

  const handleEditProject = (project: Project) => {
    navigate(`/projects/${project.id}/edit`);
  };

  const handleDeleteProject = (project: Project) => {
    confirmDialog({
      message: `Are you sure you want to delete "${project.name}"? This action cannot be undone.`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await projectService.deleteProject(project.id);
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'Project deleted successfully'
          });
          loadProjects();
        } catch (error: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: error.message || 'Failed to delete project'
          });
        }
      }
    });
  };

  // Template functions
  const nameBodyTemplate = (rowData: Project) => {
    return (
      <div className="flex align-items-center gap-2">
        <Avatar
          label={rowData.name[0].toUpperCase()}
          size="normal"
          shape="circle"
          style={{ backgroundColor: getProjectColor(rowData.project_type) }}
        />
        <div>
          <div className="font-medium">{rowData.name}</div>
          {!compact && rowData.description && (
            <div className="text-sm text-color-secondary truncate" style={{ maxWidth: '200px' }}>
              {rowData.description}
            </div>
          )}
        </div>
      </div>
    );
  };

  const typeBodyTemplate = (rowData: Project) => {
    const typeConfig = getProjectTypeConfig(rowData.project_type);
    return (
      <Tag
        value={typeConfig.label}
        icon={typeConfig.icon}
        style={{ backgroundColor: typeConfig.color }}
      />
    );
  };

  const statusBodyTemplate = (rowData: Project) => {
    const statusConfig = getProjectStatusConfig(rowData.status);
    return (
      <Tag
        value={statusConfig.label}
        severity={statusConfig.severity}
        icon={statusConfig.icon}
      />
    );
  };

  const priorityBodyTemplate = (rowData: Project) => {
    const priorityConfig = getProjectPriorityConfig(rowData.priority);
    return (
      <Tag
        value={priorityConfig.label}
        severity={priorityConfig.severity}
        icon={priorityConfig.icon}
      />
    );
  };

  const ownerBodyTemplate = (rowData: Project) => {
    if (!rowData.owner) return null;
    
    return (
      <div className="flex align-items-center gap-2">
        <Avatar
          image={rowData.owner.avatar_url}
          label={rowData.owner.username[0].toUpperCase()}
          size="normal"
          shape="circle"
        />
        <span>{rowData.owner.full_name || rowData.owner.username}</span>
      </div>
    );
  };

  const memberCountBodyTemplate = (rowData: Project) => {
    return (
      <Badge value={rowData.member_count} severity="info" />
    );
  };

  const actionsBodyTemplate = (rowData: Project) => {
    if (!showActions) return null;

    return (
      <div className="flex gap-2">
        <Button
          icon="pi pi-eye"
          size="small"
          text
          tooltip="View Project"
          onClick={() => handleViewProject(rowData)}
        />
        <Button
          icon="pi pi-pencil"
          size="small"
          text
          severity="secondary"
          tooltip="Edit Project"
          onClick={() => handleEditProject(rowData)}
        />
        <Button
          icon="pi pi-trash"
          size="small"
          text
          severity="danger"
          tooltip="Delete Project"
          onClick={() => handleDeleteProject(rowData)}
        />
      </div>
    );
  };

  // Render search and filters
  const renderHeader = () => {
    if (embedded && compact) return null;

    return (
      <div className="flex flex-column gap-3">
        <div className="flex flex-wrap gap-3 align-items-center justify-content-between">
          <div className="flex flex-wrap gap-3 align-items-center">
            <span className="p-input-icon-left">
              <i className="pi pi-search" />
              <InputText
                value={globalFilterValue}
                onChange={onGlobalFilterChange}
                placeholder="Search projects..."
                className="w-20rem"
              />
            </span>
            
            <Dropdown
              value={state.query.project_type}
              options={projectTypeOptions}
              onChange={(e) => onFilterChange('project_type', e.value)}
              placeholder="All Types"
              showClear
              className="w-12rem"
            />
            
            <Dropdown
              value={state.query.status}
              options={projectStatusOptions}
              onChange={(e) => onFilterChange('status', e.value)}
              placeholder="All Status"
              showClear
              className="w-12rem"
            />

            <Dropdown
              value={state.query.priority}
              options={projectPriorityOptions}
              onChange={(e) => onFilterChange('priority', e.value)}
              placeholder="All Priorities"
              showClear
              className="w-12rem"
            />
          </div>

          {!embedded && (
            <div className="flex gap-2">
              <Button
                label="New Project"
                icon="pi pi-plus"
                onClick={() => navigate('/projects/new')}
              />
              <Button
                icon="pi pi-refresh"
                text
                tooltip="Refresh"
                onClick={() => loadProjects()}
              />
            </div>
          )}
        </div>

        {state.loading && <ProgressBar mode="indeterminate" style={{ height: '3px' }} />}
      </div>
    );
  };

  // Render toolbar for bulk actions
  const renderToolbar = () => {
    if (embedded || state.selectedProjects.length === 0) return null;

    const leftContents = (
      <div className="flex gap-2">
        <Button
          label={`${state.selectedProjects.length} selected`}
          icon="pi pi-check-circle"
          text
        />
        <Button
          label="Delete Selected"
          icon="pi pi-trash"
          severity="danger"
          text
          onClick={() => {
            // Implement bulk delete
          }}
        />
      </div>
    );

    return <Toolbar start={leftContents} />;
  };

  const content = (
    <div className={`project-list ${compact ? 'compact' : ''}`}>
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {renderHeader()}
      {renderToolbar()}
      
      <DataTable
        value={state.projects}
        loading={state.loading}
        paginator={!compact}
        rows={state.query.page_size}
        first={(state.query.page! - 1) * state.query.page_size!}
        totalRecords={state.total}
        lazy
        onPage={onPageChange}
        onSort={onSort}
        sortField={state.query.sort_by}
        sortOrder={state.query.sort_order === 'asc' ? 1 : -1}
        selection={state.selectedProjects}
        onSelectionChange={(e) => 
          setState(prev => ({ ...prev, selectedProjects: e.value }))
        }
        selectionMode="multiple"
        dataKey="id"
        emptyMessage="No projects found"
        responsiveLayout="scroll"
        stripedRows
        size={compact ? 'small' : 'normal'}
      >
        {showActions && !compact && (
          <Column
            selectionMode="multiple"
            style={{ width: '3rem' }}
            exportable={false}
          />
        )}
        
        <Column
          field="name"
          header="Project"
          body={nameBodyTemplate}
          sortable
          style={{ minWidth: '200px' }}
        />
        
        <Column
          field="project_type"
          header="Type"
          body={typeBodyTemplate}
          sortable
          style={{ width: '120px' }}
        />
        
        <Column
          field="status"
          header="Status"
          body={statusBodyTemplate}
          sortable
          style={{ width: '120px' }}
        />
        
        <Column
          field="priority"
          header="Priority"
          body={priorityBodyTemplate}
          sortable
          style={{ width: '120px' }}
        />
        
        {!compact && (
          <Column
            field="owner"
            header="Owner"
            body={ownerBodyTemplate}
            style={{ width: '150px' }}
          />
        )}
        
        <Column
          field="member_count"
          header="Members"
          body={memberCountBodyTemplate}
          sortable
          style={{ width: '100px' }}
        />
        
        <Column
          field="created_at"
          header="Created"
          sortable
          style={{ width: '120px' }}
          body={(rowData) => new Date(rowData.created_at).toLocaleDateString()}
        />
        
        {showActions && (
          <Column
            header="Actions"
            body={actionsBodyTemplate}
            exportable={false}
            style={{ width: '120px' }}
          />
        )}
      </DataTable>
    </div>
  );

  // Wrap in card if not embedded
  if (embedded) {
    return content;
  }

  return (
    <Card
      title={!compact ? "Projects" : undefined}
      className="h-full"
    >
      {content}
    </Card>
  );
};

// Helper functions and configurations
const getProjectColor = (type: ProjectType): string => {
  const colors: Record<ProjectType, string> = {
    [ProjectType.SOFTWARE]: '#3B82F6',
    [ProjectType.WEB]: '#10B981',
    [ProjectType.MOBILE]: '#8B5CF6',
    [ProjectType.DATA_SCIENCE]: '#F59E0B',
    [ProjectType.INFRASTRUCTURE]: '#EF4444',
    [ProjectType.RESEARCH]: '#6366F1',
    [ProjectType.OTHER]: '#6B7280'
  };
  return colors[type] || '#6B7280';
};

const getProjectTypeConfig = (type: ProjectType) => {
  const configs = {
    [ProjectType.SOFTWARE]: { label: 'Software', icon: 'pi pi-code', color: '#3B82F6' },
    [ProjectType.WEB]: { label: 'Web', icon: 'pi pi-globe', color: '#10B981' },
    [ProjectType.MOBILE]: { label: 'Mobile', icon: 'pi pi-mobile', color: '#8B5CF6' },
    [ProjectType.DATA_SCIENCE]: { label: 'Data Science', icon: 'pi pi-chart-bar', color: '#F59E0B' },
    [ProjectType.INFRASTRUCTURE]: { label: 'Infrastructure', icon: 'pi pi-server', color: '#EF4444' },
    [ProjectType.RESEARCH]: { label: 'Research', icon: 'pi pi-search', color: '#6366F1' },
    [ProjectType.OTHER]: { label: 'Other', icon: 'pi pi-question-circle', color: '#6B7280' }
  };
  return configs[type];
};

const getProjectStatusConfig = (status: ProjectStatus) => {
  const configs = {
    [ProjectStatus.PLANNING]: { label: 'Planning', severity: 'info' as const, icon: 'pi pi-clock' },
    [ProjectStatus.ACTIVE]: { label: 'Active', severity: 'success' as const, icon: 'pi pi-play' },
    [ProjectStatus.ON_HOLD]: { label: 'On Hold', severity: 'warning' as const, icon: 'pi pi-pause' },
    [ProjectStatus.COMPLETED]: { label: 'Completed', severity: 'success' as const, icon: 'pi pi-check' },
    [ProjectStatus.CANCELLED]: { label: 'Cancelled', severity: 'danger' as const, icon: 'pi pi-times' },
    [ProjectStatus.ARCHIVED]: { label: 'Archived', severity: 'secondary' as const, icon: 'pi pi-archive' }
  };
  return configs[status];
};

const getProjectPriorityConfig = (priority: ProjectPriority) => {
  const configs = {
    [ProjectPriority.LOW]: { label: 'Low', severity: 'success' as const, icon: 'pi pi-arrow-down' },
    [ProjectPriority.MEDIUM]: { label: 'Medium', severity: 'warning' as const, icon: 'pi pi-minus' },
    [ProjectPriority.HIGH]: { label: 'High', severity: 'danger' as const, icon: 'pi pi-arrow-up' },
    [ProjectPriority.CRITICAL]: { label: 'Critical', severity: 'danger' as const, icon: 'pi pi-exclamation-triangle' }
  };
  return configs[priority];
};

// Dropdown options
const projectTypeOptions = Object.values(ProjectType).map(type => ({
  label: getProjectTypeConfig(type).label,
  value: type
}));

const projectStatusOptions = Object.values(ProjectStatus).map(status => ({
  label: getProjectStatusConfig(status).label,
  value: status
}));

const projectPriorityOptions = Object.values(ProjectPriority).map(priority => ({
  label: getProjectPriorityConfig(priority).label,
  value: priority
}));

export default ProjectList;