/**
 * Edit user dialog component
 */

import { useEffect, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import { getRoles, type RoleListItem } from '@/services/roles.service';
import type { User, UpdateUserRequest } from '@/services/users.service';
import { handleApiError } from '@/lib/api';

interface EditUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: User | null;
  onSubmit: (userId: string, data: UpdateUserRequest) => Promise<void>;
}

export default function EditUserDialog({ open, onOpenChange, user, onSubmit }: EditUserDialogProps) {
  const [email, setEmail] = useState('');
  const [roleId, setRoleId] = useState<number | null>(null);
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [roles, setRoles] = useState<RoleListItem[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // Load roles when dialog opens
  useEffect(() => {
    if (open) {
      loadRoles();
    }
  }, [open]);

  // Populate form when user changes
  useEffect(() => {
    if (user) {
      setEmail(user.email);
      setRoleId(user.role_id);
      setIsActive(user.is_active);
    }
  }, [user]);

  const loadRoles = async () => {
    setLoadingData(true);
    try {
      const rolesRes = await getRoles();
      setRoles(rolesRes.items);
    } catch (err) {
      console.error('Failed to load roles:', err);
    } finally {
      setLoadingData(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setLoading(true);
    setError(null);

    try {
      await onSubmit(user.id, {
        email,
        role_id: roleId!,
        is_active: isActive,
      });
      onOpenChange(false);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = email && roleId;

  return (
    <AppDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Edit User"
      description="Update user details. Account cannot be changed."
      className="max-w-md"
      footer={
        <>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button type="submit" form="edit-user-form" disabled={loading || !isFormValid || loadingData}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Update User
          </Button>
        </>
      }
    >
      {loadingData ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <form id="edit-user-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email *</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role *</Label>
            <Select
              value={roleId?.toString() || ''}
              onValueChange={(v) => setRoleId(parseInt(v))}
              disabled={loading}
            >
              <SelectTrigger id="role">
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id.toString()}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="isActive"
              checked={isActive}
              onCheckedChange={(checked) => setIsActive(checked as boolean)}
              disabled={loading}
            />
            <Label htmlFor="isActive" className="cursor-pointer">
              Active (can log in)
            </Label>
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          )}
        </form>
      )}
    </AppDialog>
  );
}
