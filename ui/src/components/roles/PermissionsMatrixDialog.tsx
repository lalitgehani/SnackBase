/**
 * Permissions Matrix Dialog
 * Dialog for viewing and editing permissions for a role across all collections
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Check, Shield, Edit, Plus, Trash2 } from 'lucide-react';
import {
  getRolePermissionsMatrix,
  updateRolePermissionsBulk,
  deletePermission,
  type RoleListItem,
  type OperationRule,
} from '@/services/roles.service';
import RuleEditor from './RuleEditor';
import FieldSelector from './FieldSelector';

interface PermissionsMatrixDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: RoleListItem | null;
  onSaved?: () => void;
}

type Operation = 'create' | 'read' | 'update' | 'delete';

const OPERATIONS: { key: Operation; label: string; color: string }[] = [
  { key: 'create', label: 'Create', color: 'bg-green-500/10 text-green-700 border-green-500/20' },
  { key: 'read', label: 'Read', color: 'bg-blue-500/10 text-blue-700 border-blue-500/20' },
  { key: 'update', label: 'Update', color: 'bg-orange-500/10 text-orange-700 border-orange-500/20' },
  { key: 'delete', label: 'Delete', color: 'bg-red-500/10 text-red-700 border-red-500/20' },
];

interface PermissionCell {
  enabled: boolean;
  rule: string;
  fields: string[] | '*';
  permission_id: number | null;
}

interface PermissionRow {
  collection: string;
  create: PermissionCell;
  read: PermissionCell;
  update: PermissionCell;
  delete: PermissionCell;
}

export default function PermissionsMatrixDialog({
  open,
  onOpenChange,
  role,
  onSaved,
}: PermissionsMatrixDialogProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<PermissionRow[]>([]);
  const [editingCell, setEditingCell] = useState<{ collection: string; operation: Operation } | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch permissions when dialog opens
  const fetchPermissions = useCallback(async () => {
    if (!role) return;

    setLoading(true);
    setError(null);

    try {
      const response = await getRolePermissionsMatrix(role.id);
      const rows = response.permissions.map((perm) => ({
        collection: perm.collection,
        create: permToCell(perm.create, perm.permission_id),
        read: permToCell(perm.read, perm.permission_id),
        update: permToCell(perm.update, perm.permission_id),
        delete: permToCell(perm.delete, perm.permission_id),
      }));

      // Ensure wildcard row is at the top
      const wildcardRow = rows.find((r) => r.collection === '*');
      const otherRows = rows.filter((r) => r.collection !== '*');
      if (wildcardRow) {
        otherRows.unshift(wildcardRow);
      } else {
        // Add wildcard row if not present
        otherRows.unshift({
          collection: '*',
          create: { enabled: false, rule: 'true', fields: '*', permission_id: null },
          read: { enabled: false, rule: 'true', fields: '*', permission_id: null },
          update: { enabled: false, rule: 'true', fields: '*', permission_id: null },
          delete: { enabled: false, rule: 'true', fields: '*', permission_id: null },
        });
      }

      setPermissions(otherRows);
      setHasChanges(false);
    } catch (err: unknown) {
      const error = err as {
        response?: { data?: { detail?: string }; status?: number };
        message?: string;
        code?: string;
      };
      console.error('Failed to load permissions:', error);
      const status = error.response?.status ? ` (${error.response.status})` : '';
      setError(
        error.response?.data?.detail ||
        error.message ||
        `Failed to load permissions${status}. Check console for details.`
      );
    } finally {
      setLoading(false);
    }
  }, [role]);

  useEffect(() => {
    if (open && role) {
      fetchPermissions();
    }
  }, [open, role, fetchPermissions]);

  const permToCell = (perm: OperationRule | null, permission_id: number | null = null): PermissionCell => {
    if (!perm) {
      return { enabled: false, rule: 'true', fields: '*', permission_id: null };
    }
    return {
      enabled: true,
      rule: perm.rule || 'true',
      fields: perm.fields || '*',
      permission_id,
    };
  };

  const handleEditCell = (collection: string, operation: Operation) => {
    setEditingCell({ collection, operation });
  };

  const handleCloseEdit = () => {
    setEditingCell(null);
  };

  const [deletedPermissionIds, setDeletedPermissionIds] = useState<Set<number>>(new Set());

  const handleDeletePermission = (collection: string, operation: Operation) => {
    // Find the permission ID to delete
    const row = permissions.find((r) => r.collection === collection);
    if (row) {
      const cell = row[operation];
      if (cell.permission_id) {
        setDeletedPermissionIds((prev) => new Set(prev).add(cell.permission_id!));
      }
    }

    const newPermissions = permissions.map((row) => {
      if (row.collection === collection) {
        return {
          ...row,
          [operation]: { enabled: false, rule: 'true', fields: '*', permission_id: null },
        };
      }
      return row;
    });
    setPermissions(newPermissions);
    setHasChanges(true);
    setEditingCell(null);
    setShowDeleteConfirm(false);
  };

  const handleSaveCell = (collection: string, operation: Operation, cell: PermissionCell) => {
    const newPermissions = permissions.map((row) => {
      if (row.collection === collection) {
        return { ...row, [operation]: cell };
      }
      return row;
    });

    setPermissions(newPermissions);
    setHasChanges(true);
    setEditingCell(null);
  };

  const handleSave = async () => {
    if (!role) return;

    setSaving(true);
    setError(null);

    try {
      // First, find all unique permission_ids that need to be deleted (collections that have any permissions)
      // and delete them entirely. Then we'll recreate with only the enabled operations.
      const permissionIdsToDelete = new Set<number | null>();
      const collectionsWithPermissions = new Set<string>();

      permissions.forEach((row) => {
        OPERATIONS.forEach((op) => {
          const cell = row[op.key];
          if (cell.permission_id) {
            permissionIdsToDelete.add(cell.permission_id);
            collectionsWithPermissions.add(row.collection);
          }
        });
      });

      // Add any explicitly deleted permissions
      deletedPermissionIds.forEach((id) => permissionIdsToDelete.add(id));

      // Delete existing permissions (this removes ALL operations for those collections)
      for (const permissionId of permissionIdsToDelete) {
        if (permissionId) {
          await deletePermission(permissionId);
        }
      }

      // Now build bulk update request with only the enabled operations
      const updates: { collection: string; operation: Operation; rule: string; fields: string[] | '*' }[] = [];

      permissions.forEach((row) => {
        OPERATIONS.forEach((op) => {
          const cell = row[op.key];
          if (cell.enabled) {
            updates.push({
              collection: row.collection,
              operation: op.key,
              rule: cell.rule,
              fields: cell.fields,
            });
          }
        });
      });

      // Only call API if there are updates to save
      if (updates.length > 0) {
        await updateRolePermissionsBulk(role.id, { updates });
      }

      setHasChanges(false);
      setDeletedPermissionIds(new Set());

      if (onSaved) {
        onSaved();
      }

      onOpenChange(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(error.response?.data?.detail || error.message || 'Failed to save permissions');
    } finally {
      setSaving(false);
    }
  };

  const getOperationCount = () => {
    let count = 0;
    permissions.forEach((row) => {
      OPERATIONS.forEach((op) => {
        if (row[op.key].enabled) count++;
      });
    });
    return count;
  };

  const getCollectionCount = () => {
    return permissions.filter((row) =>
      OPERATIONS.some((op) => row[op.key].enabled)
    ).length;
  };

  // Edit dialog for a single permission cell
  const renderEditDialog = () => {
    if (!editingCell) return null;

    const row = permissions.find((r) => r.collection === editingCell.collection);
    if (!row) return null;

    const cell = row[editingCell.operation];

    return (
      <Dialog open={!!editingCell} onOpenChange={handleCloseEdit}>
        <DialogContent className="lg:max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              Edit Permission: {editingCell.collection} - {editingCell.operation}
            </DialogTitle>
            <DialogDescription>
              Configure the rule and allowed fields for this permission
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <RuleEditor
              value={cell.rule}
              onChange={(newRule) => {
                const newPermissions = permissions.map((r) => {
                  if (r.collection === editingCell.collection) {
                    return { ...r, [editingCell.operation]: { ...r[editingCell.operation], rule: newRule } };
                  }
                  return r;
                });
                setPermissions(newPermissions);
                setHasChanges(true);
              }}
            />

            <FieldSelector
              value={cell.fields}
              onChange={(newFields) => {
                const newPermissions = permissions.map((r) => {
                  if (r.collection === editingCell.collection) {
                    return { ...r, [editingCell.operation]: { ...r[editingCell.operation], fields: newFields } };
                  }
                  return r;
                });
                setPermissions(newPermissions);
                setHasChanges(true);
              }}
              fields={[
                { name: 'id', isSystem: true },
                { name: 'account_id', isSystem: true },
                { name: 'created_at', isSystem: true },
                { name: 'updated_at', isSystem: true },
                { name: 'created_by', isSystem: true },
                { name: 'title', isSystem: false },
                { name: 'content', isSystem: false },
                { name: 'status', isSystem: false },
              ]}
            />
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="destructive"
              onClick={() => setShowDeleteConfirm(true)}
              className="mr-auto"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Permission
            </Button>
            <Button variant="outline" onClick={handleCloseEdit}>
              Cancel
            </Button>
            <Button onClick={() => handleSaveCell(editingCell.collection, editingCell.operation, cell)}>
              Save Changes
            </Button>
          </DialogFooter>

          {/* Delete Confirmation Dialog */}
          <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Permission?</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete the <strong>{editingCell?.operation}</strong> permission for <strong>{editingCell?.collection}</strong>?
                  Users will no longer have this access.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => editingCell && handleDeletePermission(editingCell.collection, editingCell.operation)}
                  className="bg-destructive text-white hover:bg-destructive/90"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </DialogContent>
      </Dialog>
    );
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="lg:max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Permissions: {role?.name}
            </DialogTitle>
            <DialogDescription>
              Configure CRUD permissions for each collection. Click the edit icon to modify rules and fields.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-hidden flex flex-col">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                <p className="text-destructive">{error}</p>
                <Button onClick={fetchPermissions} className="mt-2" size="sm">
                  Retry
                </Button>
              </div>
            ) : (
              <ScrollArea className="flex-1 pr-4 min-h-0">
                <div className="space-y-4">
                  {/* Summary */}
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>
                      {getCollectionCount()} collection{getCollectionCount() !== 1 ? 's' : ''} configured
                    </span>
                    <span>•</span>
                    <span>{getOperationCount()} operation{getOperationCount() !== 1 ? 's' : ''} enabled</span>
                    {hasChanges && (
                      <>
                        <span>•</span>
                        <Badge variant="secondary" className="text-xs">
                          Unsaved changes
                        </Badge>
                      </>
                    )}
                  </div>

                  {/* Table Header */}
                  <div className="grid grid-cols-6 gap-2 pb-2 border-b font-medium text-sm">
                    <div className="col-span-2">Collection</div>
                    {OPERATIONS.map((op) => (
                      <div key={op.key} className="text-center">
                        {op.label}
                      </div>
                    ))}
                  </div>

                  {/* Table Rows */}
                  <div className="space-y-1">
                    {permissions.map((row) => (
                      <div
                        key={row.collection}
                        className={`grid grid-cols-6 gap-2 p-2 rounded-md items-center ${row.collection === '*' ? 'bg-primary/5 border border-primary/20' : 'hover:bg-muted/50'
                          }`}
                      >
                        {/* Collection Name */}
                        <div className="col-span-2 font-medium flex items-center gap-2">
                          {row.collection}
                          {row.collection === '*' && (
                            <Badge variant="secondary" className="text-xs">
                              All Collections
                            </Badge>
                          )}
                        </div>

                        {/* Operations */}
                        {OPERATIONS.map((op) => {
                          const cell = row[op.key];
                          return (
                            <div key={op.key} className="text-center">
                              {cell.enabled ? (
                                <div
                                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border text-xs font-medium ${op.color} cursor-pointer hover:opacity-80`}
                                  onClick={() => handleEditCell(row.collection, op.key)}
                                >
                                  <Check className="h-3 w-3" />
                                  <span>{cell.rule === 'true' ? 'Allow' : 'Custom'}</span>
                                  <Edit className="h-3 w-3 ml-1 opacity-60" />
                                </div>
                              ) : (
                                <div
                                  className="inline-flex items-center justify-center gap-1 px-2 py-1 rounded-md border border-dashed text-xs font-medium text-muted-foreground cursor-pointer hover:bg-secondary/50 hover:border-secondary"
                                  onClick={() => {
                                    // Enable the permission and open edit dialog
                                    const newPermissions = permissions.map((r) => {
                                      if (r.collection === row.collection) {
                                        return {
                                          ...r,
                                          [op.key]: { enabled: true, rule: 'true', fields: '*', permission_id: null },
                                        };
                                      }
                                      return r;
                                    });
                                    setPermissions(newPermissions);
                                    setHasChanges(true);
                                    handleEditCell(row.collection, op.key);
                                  }}
                                >
                                  <Plus className="h-3 w-3" />
                                  <span>Add</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>

                  {/* Empty State */}
                  {permissions.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      <Shield className="h-12 w-12 mx-auto mb-3 opacity-30" />
                      <p>No permissions configured</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            )}
          </div>

          <DialogFooter className="border-t pt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving || !hasChanges}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {renderEditDialog()}
    </>
  );
}
