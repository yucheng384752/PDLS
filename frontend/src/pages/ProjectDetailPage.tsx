/**
 * Project Detail Page Component
 * Page wrapper for the ProjectDetail component with routing
 */

import React from 'react';
import { useParams } from 'react-router-dom';
import ProjectDetail from '../components/project/ProjectDetail';

const ProjectDetailPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <div className="project-detail-page">
      <ProjectDetail projectId={projectId} />
    </div>
  );
};

export default ProjectDetailPage;