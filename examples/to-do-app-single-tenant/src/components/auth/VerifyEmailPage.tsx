/**
 * Email verification page component
 * Handles email verification from the link sent to users
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import * as authService from '@/services/auth.service';

export default function VerifyEmailPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
    const [errorMessage, setErrorMessage] = useState('');
    const [email, setEmail] = useState('');

    useEffect(() => {
        const verifyEmail = async () => {
            const token = searchParams.get('token');

            if (!token) {
                setStatus('error');
                setErrorMessage('No verification token provided');
                return;
            }

            try {
                const response = await authService.verifyEmail(token);
                if (response.user) {
                    setEmail(response.user.email);
                }
                setStatus('success');
            } catch (error) {
                setStatus('error');
                const message = error instanceof Error ? error.message : 'Verification failed';
                setErrorMessage(message);
            }
        };

        verifyEmail();
    }, [searchParams]);

    if (status === 'verifying') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
                <Card className="w-full max-w-md">
                    <CardHeader className="space-y-1 text-center">
                        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center">
                            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                        </div>
                        <CardTitle className="text-2xl font-bold">Verifying Your Email</CardTitle>
                        <CardDescription>
                            Please wait while we verify your email address...
                        </CardDescription>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
                <Card className="w-full max-w-md">
                    <CardHeader className="space-y-1 text-center">
                        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                            <CheckCircle2 className="h-6 w-6 text-green-600" />
                        </div>
                        <CardTitle className="text-2xl font-bold">Email Verified!</CardTitle>
                        <CardDescription>
                            Your email <strong>{email}</strong> has been successfully verified.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="rounded-md bg-green-50 p-4 text-sm text-green-800">
                            <p className="font-medium mb-2">You're all set!</p>
                            <p>You can now log in to your account and start using the application.</p>
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button
                            onClick={() => navigate('/login')}
                            className="w-full"
                        >
                            Go to Login
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        );
    }

    // Error state
    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1 text-center">
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                        <XCircle className="h-6 w-6 text-red-600" />
                    </div>
                    <CardTitle className="text-2xl font-bold">Verification Failed</CardTitle>
                    <CardDescription>
                        We couldn't verify your email address.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
                        <p className="font-medium mb-2">Error:</p>
                        <p>{errorMessage || 'The verification link is invalid or has expired.'}</p>
                    </div>
                    <p className="text-sm text-gray-600 text-center">
                        Please try registering again or contact support if the problem persists.
                    </p>
                </CardContent>
                <CardFooter className="flex gap-2">
                    <Button
                        onClick={() => navigate('/register')}
                        variant="outline"
                        className="w-full"
                    >
                        Register Again
                    </Button>
                    <Button
                        onClick={() => navigate('/login')}
                        className="w-full"
                    >
                        Go to Login
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
