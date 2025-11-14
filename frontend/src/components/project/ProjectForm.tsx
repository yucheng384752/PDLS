/**
 * Project Form Component - PrimeReact Version
 * Form for creating and editing projects with validation using PrimeReact components
 */

import React from 'react';
import { Controller, useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Divider } from 'primereact/divider';
import { Chips } from 'primereact/chips';
import { classNames } from 'primereact/utils';
import { Toast } from 'primereact/toast';
import {
  Project,
  CreateProjectRequest,
  UpdateProjectRequest,
  ProjectType,
  ProjectStatus,
  ProjectPriority
} from '../../types/project';

// Form data interface that matches exactly what we need
interface ProjectFormData {
  name: string;
  description?: string;
  project_type: ProjectType;
  status: ProjectStatus;
  priority: ProjectPriority;
  start_date?: Date | null;
  end_date?: Date | null;
  repository_url?: string;
  documentation_url?: string;
  tags?: string[];
}

// Validation schema using Yup
const projectFormSchema = yup.object().shape({
  name: yup
    .string()
    .required('Project name is required')
    .min(3, 'Project name must be at least 3 characters')
    .max(200, 'Project name cannot exceed 200 characters'),
  description: yup
    .string()
    .max(2000, 'Description cannot exceed 2000 characters')
    .optional(),
  project_type: yup
    .string()
    .oneOf(Object.values(ProjectType))
    .required('Project type is required'),
  status: yup
    .string()
    .oneOf(Object.values(ProjectStatus))
    .required('Status is required'),
  priority: yup
    .string()
    .oneOf(Object.values(ProjectPriority))
    .required('Priority is required'),
  start_date: yup
    .date()
    .nullable()
    .optional(),
  end_date: yup
    .date()
    .nullable()
    .optional()
    .when('start_date', (start_date, schema) => {
      return start_date
        ? schema.min(start_date, 'End date must be after start date')
        : schema;
    }),
  repository_url: yup
    .string()
    .url('Please enter a valid URL')
    .optional(),
  documentation_url: yup
    .string()
    .url('Please enter a valid URL')
    .optional(),
  tags: yup.array().of(yup.string().required()).optional()
});

interface ProjectFormProps {
  project?: Project;
  onSubmit: (data: CreateProjectRequest | UpdateProjectRequest) => Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
}

const ProjectForm: React.FC<ProjectFormProps> = ({
  project,
  onSubmit,
  onCancel,
  loading = false
}) => {
  const isEditMode = Boolean(project);
  const toast = React.useRef<Toast>(null);

  // Form configuration with React Hook Form
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },

  } = useForm({
    resolver: yupResolver(projectFormSchema),
    defaultValues: {
      name: project?.name || '',
      description: project?.description || '',
      project_type: project?.project_type || ProjectType.SOFTWARE,
      status: project?.status || ProjectStatus.PLANNING,
      priority: project?.priority || ProjectPriority.MEDIUM,
      start_date: project?.start_date ? new Date(project.start_date) : null,
      end_date: project?.end_date ? new Date(project.end_date) : null,
      repository_url: project?.repository_url || '',
      documentation_url: project?.documentation_url || '',
      tags: project?.tags || []
    }
  });

  // Form submission handler
  const onFormSubmit = async (data: ProjectFormData) => {
    try {
      // Convert Date objects to ISO strings for API and clean up empty values
      const formattedData: CreateProjectRequest = {
        name: data.name,
        project_type: data.project_type,
        status: data.status,
        priority: data.priority,
        description: data.description || undefined,
        start_date: data.start_date ? data.start_date.toISOString() : undefined,
        end_date: data.end_date ? data.end_date.toISOString() : undefined,
        repository_url: data.repository_url || undefined,
        documentation_url: data.documentation_url || undefined,
        tags: data.tags || undefined
      };
      
      await onSubmit(formattedData);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `Project ${isEditMode ? 'updated' : 'created'} successfully`
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.message || `Failed to ${isEditMode ? 'update' : 'create'} project`
      });
    }
  };

  // Field error helper
  const getFormErrorMessage = (name: keyof CreateProjectRequest) => {
    return errors[name] ? (
      <small className="p-error">{errors[name]?.message}</small>
    ) : null;
  };

  // Dropdown options
  const projectTypeOptions = [
    { label: 'Software', value: ProjectType.SOFTWARE },
    { label: 'Web Application', value: ProjectType.WEB },
    { label: 'Mobile App', value: ProjectType.MOBILE },
    { label: 'Data Science', value: ProjectType.DATA_SCIENCE },
    { label: 'Infrastructure', value: ProjectType.INFRASTRUCTURE },
    { label: 'Research', value: ProjectType.RESEARCH },
    { label: 'Other', value: ProjectType.OTHER }
  ];

  const projectStatusOptions = [
    { label: 'Planning', value: ProjectStatus.PLANNING },
    { label: 'Active', value: ProjectStatus.ACTIVE },
    { label: 'On Hold', value: ProjectStatus.ON_HOLD },
    { label: 'Completed', value: ProjectStatus.COMPLETED },
    { label: 'Cancelled', value: ProjectStatus.CANCELLED },
    { label: 'Archived', value: ProjectStatus.ARCHIVED }
  ];

  const projectPriorityOptions = [
    { label: 'Low', value: ProjectPriority.LOW },
    { label: 'Medium', value: ProjectPriority.MEDIUM },
    { label: 'High', value: ProjectPriority.HIGH },
    { label: 'Critical', value: ProjectPriority.CRITICAL }
  ];

  return (
    <div className="project-form">
      <Toast ref={toast} />
      
      <Card 
        title={isEditMode ? 'Edit Project' : 'Create New Project'}
        className="p-mb-4"
      >
        <form onSubmit={handleSubmit(onFormSubmit)} className="p-fluid">
          
          {/* Basic Information */}
          <div className="p-field-group">
            <h4 className="p-text-bold p-mb-3">Basic Information</h4>
            
            {/* Project Name */}
            <div className="p-field p-mb-3">
              <label htmlFor="name" className="p-text-bold">
                Project Name <span className="p-error">*</span>
              </label>
              <Controller
                name="name"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <InputText
                      {...field}
                      id="name"
                      placeholder="Enter project name"
                      className={classNames({ 'p-invalid': fieldState.error })}
                      disabled={loading}
                    />
                    {getFormErrorMessage('name')}
                  </>
                )}
              />
            </div>

            {/* Description */}
            <div className="p-field p-mb-3">
              <label htmlFor="description" className="p-text-bold">Description</label>
              <Controller
                name="description"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <InputTextarea
                      {...field}
                      id="description"
                      placeholder="Enter project description"
                      rows={4}
                      className={classNames({ 'p-invalid': fieldState.error })}
                      disabled={loading}
                    />
                    {getFormErrorMessage('description')}
                  </>
                )}
              />
            </div>
          </div>

          <Divider />

          {/* Project Settings */}
          <div className="p-field-group">
            <h4 className="p-text-bold p-mb-3">Project Settings</h4>
            
            <div className="p-formgrid p-grid">
              {/* Project Type */}
              <div className="p-field p-col-12 p-md-4">
                <label htmlFor="project_type" className="p-text-bold">
                  Project Type <span className="p-error">*</span>
                </label>
                <Controller
                  name="project_type"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Dropdown
                        {...field}
                        id="project_type"
                        options={projectTypeOptions}
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select project type"
                        className={classNames({ 'p-invalid': fieldState.error })}
                        disabled={loading}
                      />
                      {getFormErrorMessage('project_type')}
                    </>
                  )}
                />
              </div>

              {/* Status */}
              <div className="p-field p-col-12 p-md-4">
                <label htmlFor="status" className="p-text-bold">Status</label>
                <Controller
                  name="status"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Dropdown
                        {...field}
                        id="status"
                        options={projectStatusOptions}
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select status"
                        className={classNames({ 'p-invalid': fieldState.error })}
                        disabled={loading}
                      />
                      {getFormErrorMessage('status')}
                    </>
                  )}
                />
              </div>

              {/* Priority */}
              <div className="p-field p-col-12 p-md-4">
                <label htmlFor="priority" className="p-text-bold">Priority</label>
                <Controller
                  name="priority"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Dropdown
                        {...field}
                        id="priority"
                        options={projectPriorityOptions}
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select priority"
                        className={classNames({ 'p-invalid': fieldState.error })}
                        disabled={loading}
                      />
                      {getFormErrorMessage('priority')}
                    </>
                  )}
                />
              </div>
            </div>
          </div>

          <Divider />

          {/* Timeline */}
          <div className="p-field-group">
            <h4 className="p-text-bold p-mb-3">Timeline</h4>
            
            <div className="p-formgrid p-grid">
              {/* Start Date */}
              <div className="p-field p-col-12 p-md-6">
                <label htmlFor="start_date" className="p-text-bold">Start Date</label>
                <Controller
                  name="start_date"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Calendar
                        {...field}
                        id="start_date"
                        placeholder="Select start date"
                        showIcon
                        dateFormat="yy-mm-dd"
                        className={classNames({ 'p-invalid': fieldState.error })}
                        disabled={loading}
                      />
                      {getFormErrorMessage('start_date')}
                    </>
                  )}
                />
              </div>

              {/* End Date */}
              <div className="p-field p-col-12 p-md-6">
                <label htmlFor="end_date" className="p-text-bold">End Date</label>
                <Controller
                  name="end_date"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Calendar
                        {...field}
                        id="end_date"
                        placeholder="Select end date"
                        showIcon
                        dateFormat="yy-mm-dd"
                        className={classNames({ 'p-invalid': fieldState.error })}
                        disabled={loading}
                      />
                      {getFormErrorMessage('end_date')}
                    </>
                  )}
                />
              </div>
            </div>
          </div>

          <Divider />

          {/* Links */}
          <div className="p-field-group">
            <h4 className="p-text-bold p-mb-3">Links</h4>
            
            {/* Repository URL */}
            <div className="p-field p-mb-3">
              <label htmlFor="repository_url" className="p-text-bold">Repository URL</label>
              <Controller
                name="repository_url"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <InputText
                      {...field}
                      id="repository_url"
                      placeholder="https://github.com/user/repo"
                      className={classNames({ 'p-invalid': fieldState.error })}
                      disabled={loading}
                    />
                    {getFormErrorMessage('repository_url')}
                  </>
                )}
              />
            </div>

            {/* Documentation URL */}
            <div className="p-field p-mb-3">
              <label htmlFor="documentation_url" className="p-text-bold">Documentation URL</label>
              <Controller
                name="documentation_url"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <InputText
                      {...field}
                      id="documentation_url"
                      placeholder="https://docs.example.com"
                      className={classNames({ 'p-invalid': fieldState.error })}
                      disabled={loading}
                    />
                    {getFormErrorMessage('documentation_url')}
                  </>
                )}
              />
            </div>
          </div>

          <Divider />

          {/* Tags */}
          <div className="p-field-group">
            <h4 className="p-text-bold p-mb-3">Tags</h4>
            
            <div className="p-field">
              <label htmlFor="tags" className="p-text-bold">Project Tags</label>
              <Controller
                name="tags"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <Chips
                      id="tags"
                      value={field.value || []}
                      onChange={(e) => field.onChange(e.value)}
                      placeholder="Add tags (press Enter to add)"
                      className={classNames({ 'p-invalid': fieldState.error })}
                      disabled={loading}
                    />
                    {getFormErrorMessage('tags')}
                  </>
                )}
              />
            </div>
          </div>

          <Divider />

          {/* Form Actions */}
          <div className="p-field-group p-text-center">
            <Button
              type="submit"
              label={isEditMode ? 'Update Project' : 'Create Project'}
              icon={isEditMode ? 'pi pi-check' : 'pi pi-plus'}
              className="p-mr-2"
              loading={loading || isSubmitting}
              disabled={loading}
            />
            
            {onCancel && (
              <Button
                type="button"
                label="Cancel"
                icon="pi pi-times"
                className="p-button-secondary"
                onClick={onCancel}
                disabled={loading || isSubmitting}
              />
            )}
          </div>
        </form>
      </Card>
    </div>
  );
};

export default ProjectForm;