/**
 * Project Members Component
 * Manages project members, invitations, and role assignments
 */

import React, { useState, useRef } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Avatar } from 'primereact/avatar';
import { Badge } from 'primereact/badge';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { Dialog } from 'primereact/dialog';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Toolbar } from 'primereact/toolbar';
import { Skeleton } from 'primereact/skeleton';
import { 
  ProjectMember, 
  ProjectMemberRole,
  CreateInvitationRequest,
  ProjectUser
} from '../../types/project';
import { projectService } from '../../services/projectService';

interface ProjectMembersProps {
  projectId: number;
  members: ProjectMember[];
  userRole: ProjectMemberRole | null;
  loading: boolean;
  onRefresh: () => void;
  onMemberUpdate: (members: ProjectMember[]) => void;
}

interface InviteFormData {
  email: string;
  role: ProjectMemberRole;
  message: string;
}

const ProjectMembers: React.FC<ProjectMembersProps> = ({
  projectId,
  members,
  userRole,
  loading,
  onRefresh,
  onMemberUpdate
}) => {
  const toast = useRef<Toast>(null);
  const [inviteDialogVisible, setInviteDialogVisible] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);

  const [inviteForm, setInviteForm] = useState<InviteFormData>({
    email: '',
    role: ProjectMemberRole.MEMBER,
    message: ''
  });

  // Role options
  const roleOptions = [
    { label: 'Viewer', value: ProjectMemberRole.VIEWER, icon: 'pi pi-eye' },
    { label: 'Member', value: ProjectMemberRole.MEMBER, icon: 'pi pi-user' },
    { label: 'Admin', value: ProjectMemberRole.ADMIN, icon: 'pi pi-shield' },
    { label: 'Owner', value: ProjectMemberRole.OWNER, icon: 'pi pi-crown' }
  ];

  // Check if current user can manage members
  const canManageMembers = userRole && ['owner', 'admin'].includes(userRole);
  const canInviteMembers = canManageMembers;
  const canRemoveMembers = userRole === 'owner';
  const canChangeRoles = userRole === 'owner';

  // Member avatar template
  const memberAvatarTemplate = (rowData: ProjectMember) => {
    return (
      <div className="p-d-flex p-ai-center p-gap-2">
        <Avatar
          label={rowData.user?.username?.charAt(0).toUpperCase()}
          shape="circle"
          style={{ width: '32px', height: '32px' }}
        />
        <div>
          <div className="p-text-bold">{rowData.user?.full_name || rowData.user?.username}</div>
          <small className="p-text-secondary">{rowData.user?.email}</small>
        </div>
      </div>
    );
  };

  // Role badge template
  const roleBadgeTemplate = (rowData: ProjectMember) => {
    let severity: "success" | "info" | "warning" | "danger" = 'info';
    switch (rowData.role) {
      case ProjectMemberRole.OWNER:
        severity = 'danger';
        break;
      case ProjectMemberRole.ADMIN:
        severity = 'warning';
        break;
      case ProjectMemberRole.MEMBER:
        severity = 'success';
        break;
      case ProjectMemberRole.VIEWER:
        severity = 'info';
        break;
    }
    return <Badge value={rowData.role} severity={severity} />;
  };

  // Role editor template
  const roleEditorTemplate = (rowData: ProjectMember) => {
    if (!canChangeRoles || rowData.role === ProjectMemberRole.OWNER) {
      return roleBadgeTemplate(rowData);
    }

    return (
      <Dropdown
        value={rowData.role}
        options={roleOptions.filter(opt => opt.value !== ProjectMemberRole.OWNER)}
        onChange={(e) => handleRoleChange(rowData, e.value)}
        optionLabel="label"
        optionValue="value"
        className="p-dropdown-sm"
      />
    );
  };

  // Joined date template
  const joinedDateTemplate = (rowData: ProjectMember) => {
    return new Date(rowData.joined_at).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Actions template
  const actionsTemplate = (rowData: ProjectMember) => {
    if (!canRemoveMembers || rowData.role === ProjectMemberRole.OWNER) {
      return null;
    }

    return (
      <div className="p-d-flex p-gap-2">
        <Button
          icon="pi pi-trash"
          className="p-button-rounded p-button-danger p-button-outlined p-button-sm"
          tooltip="Remove member"
          onClick={() => handleRemoveMember(rowData)}
        />
      </div>
    );
  };

  // Handle role change
  const handleRoleChange = async (member: ProjectMember, newRole: ProjectMemberRole) => {
    try {
      await projectService.updateMemberRole(projectId, member.id, { role: newRole });
      
      // Update local state
      const updatedMembers = members.map(m => 
        m.id === member.id ? { ...m, role: newRole } : m
      );
      onMemberUpdate(updatedMembers);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `Member role updated to ${newRole}`
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to update member role'
      });
    }
  };

  // Handle remove member
  const handleRemoveMember = (member: ProjectMember) => {
    confirmDialog({
      message: `Are you sure you want to remove ${member.user?.full_name || member.user?.username} from this project?`,
      header: 'Remove Member',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          await projectService.removeMember(projectId, member.id);
          
          // Update local state
          const updatedMembers = members.filter(m => m.id !== member.id);
          onMemberUpdate(updatedMembers);
          
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'Member removed from project'
          });
        } catch (error: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: error.response?.data?.message || 'Failed to remove member'
          });
        }
      }
    });
  };

  // Handle invite member
  const handleInviteMember = async () => {
    if (!inviteForm.email.trim()) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Warning',
        detail: 'Please enter an email address'
      });
      return;
    }

    setInviteLoading(true);
    try {
      const invitationData: CreateInvitationRequest = {
        project_id: projectId,
        invited_email: inviteForm.email,
        role: inviteForm.role,
        message: inviteForm.message.trim() || undefined
      };

      await projectService.sendInvitation(invitationData);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Invitation sent successfully'
      });
      
      // Reset form and close dialog
      setInviteForm({
        email: '',
        role: ProjectMemberRole.MEMBER,
        message: ''
      });
      setInviteDialogVisible(false);
      
      // Refresh member list
      onRefresh();
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.message || 'Failed to send invitation'
      });
    } finally {
      setInviteLoading(false);
    }
  };



  // Invite dialog footer
  const inviteDialogFooter = (
    <div>
      <Button
        label="Cancel"
        icon="pi pi-times"
        className="p-button-text"
        onClick={() => setInviteDialogVisible(false)}
      />
      <Button
        label="Send Invitation"
        icon="pi pi-send"
        loading={inviteLoading}
        onClick={handleInviteMember}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="project-members-loading">
        <Skeleton width="100%" height="3rem" className="p-mb-3" />
        <Skeleton width="100%" height="400px" />
      </div>
    );
  }

  return (
    <div className="project-members">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Members Header */}
      <Card>
        <Toolbar
          left={
            <div className="p-d-flex p-ai-center p-gap-3">
              <h3 className="p-m-0">Project Members</h3>
              <Badge value={members.length} />
            </div>
          }
          right={
            canInviteMembers && (
              <Button
                label="Invite Member"
                icon="pi pi-user-plus"
                onClick={() => setInviteDialogVisible(true)}
              />
            )
          }
        />

        {/* Members Table */}
        <div className="p-mt-3">
          <DataTable
            value={members}
            responsiveLayout="scroll"
            emptyMessage="No members found"
            rows={10}
            paginator={members.length > 10}
          >
            <Column
              field="user"
              header="Member"
              body={memberAvatarTemplate}
              style={{ width: '300px' }}
            />
            <Column
              field="role"
              header="Role"
              body={roleEditorTemplate}
              style={{ width: '150px' }}
            />
            <Column
              field="joined_at"
              header="Joined"
              body={joinedDateTemplate}
              style={{ width: '120px' }}
            />
            {canRemoveMembers && (
              <Column
                body={actionsTemplate}
                style={{ width: '100px' }}
                bodyClassName="p-text-center"
              />
            )}
          </DataTable>
        </div>
      </Card>

      {/* Invite Member Dialog */}
      <Dialog
        header="Invite New Member"
        visible={inviteDialogVisible}
        onHide={() => setInviteDialogVisible(false)}
        footer={inviteDialogFooter}
        style={{ width: '450px' }}
        modal
      >
        <div className="invite-form p-fluid">
          <div className="p-field p-mb-4">
            <label htmlFor="email" className="p-text-bold">Email Address *</label>
            <InputText
              id="email"
              type="email"
              placeholder="Enter email address"
              value={inviteForm.email}
              onChange={(e) => setInviteForm(prev => ({ ...prev, email: e.target.value }))}
              className="p-mt-2"
            />
          </div>

          <div className="p-field p-mb-4">
            <label htmlFor="role" className="p-text-bold">Role</label>
            <Dropdown
              id="role"
              value={inviteForm.role}
              options={roleOptions.filter(opt => opt.value !== ProjectMemberRole.OWNER)}
              onChange={(e) => setInviteForm(prev => ({ ...prev, role: e.value }))}
              optionLabel="label"
              optionValue="value"
              placeholder="Select role"
              className="p-mt-2"
            />
          </div>

          <div className="p-field">
            <label htmlFor="message" className="p-text-bold">Personal Message (Optional)</label>
            <InputText
              id="message"
              placeholder="Add a personal message to the invitation"
              value={inviteForm.message}
              onChange={(e) => setInviteForm(prev => ({ ...prev, message: e.target.value }))}
              className="p-mt-2"
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default ProjectMembers;