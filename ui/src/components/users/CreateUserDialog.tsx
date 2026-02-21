/**
 * Create user dialog component
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
import { getAccounts, type Account } from '@/services/accounts.service';
import { getRoles, type RoleListItem } from '@/services/roles.service';
import type { CreateUserRequest } from '@/services/users.service';
import { handleApiError } from '@/lib/api';

interface CreateUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateUserRequest) => Promise<void>;
}

export default function CreateUserDialog({ open, onOpenChange, onSubmit }: CreateUserDialogProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountId, setAccountId] = useState('');
  const [roleId, setRoleId] = useState<number | null>(null);
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [roles, setRoles] = useState<RoleListItem[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // Load accounts and roles when dialog opens
  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    setLoadingData(true);
    try {
      const [accountsRes, rolesRes] = await Promise.all([
        getAccounts({ page_size: 100 }),
        getRoles(),
      ]);
      setAccounts(accountsRes.items);
      setRoles(rolesRes.items);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoadingData(false);
    }
  };

  const validatePassword = (): boolean => {
    if (password.length < 12) {
      setPasswordError('Password must be at least 12 characters');
      return false;
    }
    if (!/[A-Z]/.test(password)) {
      setPasswordError('Password must contain at least one uppercase letter');
      return false;
    }
    if (!/[a-z]/.test(password)) {
      setPasswordError('Password must contain at least one lowercase letter');
      return false;
    }
    if (!/\d/.test(password)) {
      setPasswordError('Password must contain at least one digit');
      return false;
    }
    // Use a simpler approach - just check for common special characters
    const specialChars = /[-!@#$%^&*()_=\\[\]{};':"\\|,.<>]/;
    if (!specialChars.test(password)) {
      setPasswordError('Password must contain at least one special character');
      return false;
    }
    if (password !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return false;
    }
    setPasswordError(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!validatePassword()) {
      setLoading(false);
      return;
    }

    try {
      await onSubmit({
        email,
        password,
        account_id: accountId,
        role_id: roleId!,
        is_active: isActive,
      });
      // Reset form
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setAccountId('');
      setRoleId(null);
      setIsActive(true);
      setPasswordError(null);
      onOpenChange(false);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = email && password && confirmPassword && accountId && roleId;

  return (
    <AppDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Create User"
      description="Create a new user in any account. The user will be able to log in immediately."
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
          <Button type="submit" form="create-user-form" disabled={loading || !isFormValid || loadingData}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create User
          </Button>
        </>
      }
    >
      {loadingData ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <form id="create-user-form" onSubmit={handleSubmit} className="space-y-4">
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
            <Label htmlFor="password">Password *</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              Min 12 chars, uppercase, lowercase, digit, special char
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password *</Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="account">Account *</Label>
            <Select
              value={accountId}
              onValueChange={setAccountId}
              disabled={loading}
            >
              <SelectTrigger id="account">
                <SelectValue placeholder="Select an account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name} ({account.account_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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

          {passwordError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {passwordError}
            </div>
          )}

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
