import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, AlertTriangle, Mail, Key } from 'lucide-react';
import type { User, PasswordResetRequest } from '@/services/users.service';
import { handleApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface ResetPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: User | null;
  onSubmit: (userId: string, data: PasswordResetRequest) => Promise<void>;
}

export default function ResetPasswordDialog({
  open,
  onOpenChange,
  user,
  onSubmit,
}: ResetPasswordDialogProps) {
  const { toast } = useToast();
  const [mode, setMode] = useState<'link' | 'password'>('link');
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

    const data: PasswordResetRequest = {};

    if (mode === 'link') {
      data.send_reset_link = true;
    } else {
      if (!validatePassword()) {
        setLoading(false);
        return;
      }
      data.new_password = password;
    }

    try {
      await onSubmit(user.id, data);

      toast({
        title: "Success",
        description: mode === 'link'
          ? `Password reset link sent to ${user.email}`
          : "Password updated successfully",
      });

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

  const isFormValid = mode === 'link' || (password && confirmPassword);

  return (
    <AppDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Reset Password"
      description={`Choose how you want to reset the password for ${user?.email}.`}
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
          <Button
            type="submit"
            form="reset-password-form"
            disabled={loading || !isFormValid}
            variant={mode === 'password' ? 'destructive' : 'default'}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === 'link' ? 'Send Reset Link' : 'Reset Password'}
          </Button>
        </>
      }
    >
      <form id="reset-password-form" onSubmit={handleSubmit}>
        <Tabs value={mode} onValueChange={(v) => setMode(v as 'link' | 'password')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="link" className="gap-2">
              <Mail className="h-4 w-4" />
              Send Link
            </TabsTrigger>
            <TabsTrigger value="password" className="gap-2">
              <Key className="h-4 w-4" />
              Set Directly
            </TabsTrigger>
          </TabsList>

          <TabsContent value="link" className="space-y-4 pt-4">
            <div className="text-sm text-balance text-muted-foreground bg-muted p-4 rounded-lg border">
              This will send a secure password reset link to <span className="font-semibold text-foreground">{user?.email}</span>.
              The user can follow the link to set their own password. The link will expire in 1 hour.
            </div>
          </TabsContent>

          <TabsContent value="password" className="space-y-4 pt-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This will immediately change the user's password and force them to log in again on all devices.
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
                required={mode === 'password'}
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
                required={mode === 'password'}
                disabled={loading}
              />
            </div>

            {passwordError && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                {passwordError}
              </div>
            )}
          </TabsContent>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md mt-4">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          )}
        </Tabs>
      </form>
    </AppDialog>
  );
}
