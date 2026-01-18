/**
 * Register page component
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { useAuthStore } from '@/stores/auth.store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Check, X, Mail } from 'lucide-react';
import OAuthButton from '@/components/ui/oauthButton';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, isLoading, error, clearError } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  // Password validation
  const passwordRequirements = {
    minLength: password.length >= 12,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?~]/.test(password),
  };

  const isPasswordValid = Object.values(passwordRequirements).every(Boolean);


  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();

    if (password !== confirmPassword) {
      return;
    }

    if (!isPasswordValid) {
      return;
    }

    try {
      await register(email, password);
      setRegistrationSuccess(true);
    } catch (err) {
      console.error('Registration failed:', err);
    }
  };

  // Show success message after registration
  if (registrationSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <Mail className="h-6 w-6 text-green-600" />
            </div>
            <CardTitle className="text-2xl font-bold">Check Your Email</CardTitle>
            <CardDescription>
              We've sent a verification link to <strong>{email}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md bg-blue-50 p-4 text-sm text-blue-800">
              <p className="font-medium mb-2">Next steps:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Check your email inbox</li>
                <li>Click the verification link</li>
                <li>Return here to log in</li>
              </ol>
            </div>
            <p className="text-xs text-gray-500 text-center">
              Didn't receive the email? Check your spam folder or contact support.
            </p>
          </CardContent>
          <CardFooter>
            <Button
              onClick={() => navigate(`/login?email=${email}`)}
              className="w-full"
            >
              Go to Login
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Create an Account</CardTitle>
          <CardDescription>
            Sign up to start managing your todos with SnackBase
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
                {error}
              </div>
            )}
            {password && confirmPassword && password !== confirmPassword && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
                Passwords do not match
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
              {password && (
                <div className="space-y-1 rounded-md border border-gray-200 bg-gray-50 p-3">
                  <p className="text-xs font-medium text-gray-700">Password requirements:</p>
                  <div className="space-y-1">
                    <Requirement met={passwordRequirements.minLength} text="At least 12 characters" />
                    <Requirement met={passwordRequirements.hasUppercase} text="Contains uppercase letter" />
                    <Requirement met={passwordRequirements.hasLowercase} text="Contains lowercase letter" />
                    <Requirement met={passwordRequirements.hasNumber} text="Contains number" />
                    <Requirement met={passwordRequirements.hasSpecial} text="Contains special character" />
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || !isPasswordValid || password !== confirmPassword}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-gray-500">Or continue with</span>
              </div>
            </div>

            <OAuthButton
              provider="google"
              onSuccess={() => navigate('/todos')}
              onError={(error) => console.error('OAuth error:', error)}
            />

            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link to="/login" className="text-blue-600 hover:underline">
                Login here
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

function Requirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {met ? (
        <Check className="h-3.5 w-3.5 text-green-600" />
      ) : (
        <X className="h-3.5 w-3.5 text-gray-400" />
      )}
      <span className={met ? 'text-green-700' : 'text-gray-500'}>{text}</span>
    </div>
  );
}
