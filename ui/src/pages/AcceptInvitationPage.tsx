
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { getInvitation, acceptInvitation, type InvitationPublicResponse } from "@/services/invitations.service";
import { InvitationPasswordForm } from "@/components/invitations/InvitationPasswordForm";
import { useAuthStore } from "@/stores/auth.store";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function AcceptInvitationPage() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");
    const navigate = useNavigate();
    const setAuth = useAuthStore((state) => state.setAuth);

    const [invitation, setInvitation] = useState<InvitationPublicResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!token) {
            setError("Invitation token is missing.");
            setLoading(false);
            return;
        }

        const fetchInvitation = async () => {
            try {
                const data = await getInvitation(token);
                setInvitation(data);
            } catch (err: any) {
                // Handle specific errors from backend
                const message = err.response?.data?.message || "Invalid or expired invitation.";
                setError(message);
            } finally {
                setLoading(false);
            }
        };

        fetchInvitation();
    }, [token]);

    const handleAccept = async (password: string) => {
        if (!token) return;

        setSubmitting(true);
        setSubmitError(null);

        try {
            const response = await acceptInvitation(token, { password });

            // Successfully accepted, set auth state
            setAuth(response);

            // Redirect based on role
            // Only admins/superadmins should access the admin dashboard
            if (response.user.role === 'admin' || response.user.role === 'superadmin') {
                navigate("/admin/dashboard", { replace: true });
            } else {
                setSuccess(true);
            }
        } catch (err: any) {
            console.error("Failed to accept invitation:", err);
            const message = err.response?.data?.message || err.response?.data?.error || "Failed to accept invitation. Please try again.";
            setSubmitError(message);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (success) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                <Card className="w-full max-w-md mx-auto shadow-lg border-green-500/50">
                    <CardContent className="pt-6 text-center space-y-4">
                        <div className="mx-auto w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                            <svg
                                className="w-6 h-6 text-green-600"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M5 13l4 4L19 7"
                                />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Welcome to SnackBase!</h2>
                        <p className="text-muted-foreground">
                            Your account has been successfully created and you have joined <strong>{invitation?.account_name}</strong>.
                        </p>
                        <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-900">
                            <AlertDescription className="text-blue-800 dark:text-blue-200">
                                You can now log in to the application using your credentials.
                            </AlertDescription>
                        </Alert>
                        <div className="pt-2">
                            <p className="text-sm text-gray-500">
                                (This is an admin portal. As a regular user, you may not have access to the dashboard features here.)
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (error || !invitation) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                <Card className="w-full max-w-md mx-auto shadow-lg border-destructive/50">
                    <CardContent className="pt-6">
                        <Alert variant="destructive">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>Invitation Error</AlertTitle>
                            <AlertDescription>{error || "Invitation not found."}</AlertDescription>
                        </Alert>
                        <div className="mt-4 text-center">
                            <a href="/admin/login" className="text-sm text-primary hover:underline">Return to Login</a>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
            <InvitationPasswordForm
                email={invitation.email}
                accountName={invitation.account_name}
                invitedByName={invitation.invited_by_name}
                isLoading={submitting}
                error={submitError}
                onSubmit={handleAccept}
            />
        </div>
    );
}
