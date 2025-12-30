import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    Field,
    FieldGroup,
    FieldLabel,
    FieldError,
} from '@/components/ui/field';
import { useAuthStore } from '@/stores/auth.store';
import { handleApiError } from '@/lib/api';

// Validation schema
const loginSchema = z.object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
    const navigate = useNavigate();
    const login = useAuthStore((state) => state.login);
    const [error, setError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginFormData) => {
        setError(null);

        try {
            await login(data.email, data.password);
            navigate('/admin/dashboard');
        } catch (err) {
            const errorMessage = handleApiError(err);
            setError(errorMessage);
        }
    };

    return (
        <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
            <div className="w-full max-w-sm">
                <Card>
                    <CardHeader className="text-left py-4">
                        <CardTitle className="text-2xl font-semibold tracking-tight">
                            Login to your account
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                            Enter your email below to login to your account
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)}>
                            <FieldGroup>
                                <Field>
                                    <FieldLabel htmlFor="email" className="text-sm font-medium">
                                        Email
                                    </FieldLabel>
                                    <Input
                                        id="email"
                                        type="email"
                                        placeholder="m@example.com"
                                        {...register('email')}
                                        disabled={isSubmitting}
                                    />
                                    <FieldError errors={[errors.email]} />
                                </Field>
                                <Field>
                                    <div className="flex items-center">
                                        <FieldLabel
                                            htmlFor="password"
                                            className="text-sm font-medium"
                                        >
                                            Password
                                        </FieldLabel>

                                    </div>
                                    <Input
                                        id="password"
                                        type="password"
                                        {...register('password')}
                                        disabled={isSubmitting}
                                    />
                                    <FieldError errors={[errors.password]} />
                                </Field>

                                {error && (
                                    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
                                        <p className="text-sm text-destructive">{error}</p>
                                    </div>
                                )}

                                <Field className="gap-4">
                                    <Button type="submit" className="w-full" disabled={isSubmitting}>
                                        {isSubmitting ? (
                                            <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                Logging in...
                                            </>
                                        ) : (
                                            'Login'
                                        )}
                                    </Button>


                                </Field>
                            </FieldGroup>
                        </form>
                    </CardContent>
                </Card>
                <div className="text-balance text-muted-foreground text-center text-xs mt-6 px-8 leading-relaxed">
                    This is the superadmin login for SnackBase. Only authorized personnel should
                    access this area.
                </div>
            </div>
        </div>
    );
}
