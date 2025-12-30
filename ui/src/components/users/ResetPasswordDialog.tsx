/**
 * Reset password dialog component
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertTriangle } from 'lucide-react';
import type { User } from '@/services/users.service';
import { handleApiError } from '@/lib/api';

interface ResetPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: User | null;
  onSubmit: (userId: string, data: { new_password: string }) => Promise<void>;
}

export default function ResetPasswordDialog({
  open,
  onOpenChange,
  user,
  onSubmit,
}: ResetPasswordDialogProps) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

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
    if (!user) return;

    setLoading(true);
    setError(null);

    if (!validatePassword()) {
      setLoading(false);
      return;
    }

    try {
      await onSubmit(user.id, { new_password: password });
      // Reset form
      setPassword('');
      setConfirmPassword('');
      setPasswordError(null);
      onOpenChange(false);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = password && confirmPassword;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Reset password for {user?.email}. This will invalidate all of their active sessions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This will force the user to log in again on all devices.
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label htmlFor="password">New Password *</Label>
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
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !isFormValid} variant="destructive">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reset Password
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
