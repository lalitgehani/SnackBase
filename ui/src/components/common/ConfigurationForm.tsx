import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { adminService, type ProviderSchema } from '@/services/admin.service';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import {
    Field,
    FieldLabel,
    FieldContent,
    FieldError
} from '@/components/ui/field';
import { Loader2, Lock, CheckCircle2, XCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ProviderLogo } from './ProviderLogo';
import { Badge } from '@/components/ui/badge';
import { TagInput } from '@/components/ui/tag-input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';


interface ConfigurationFormProps {
    category: string;
    providerName: string;
    displayName: string;
    logoUrl?: string;
    configId?: string;
    accountId?: string;
    onSuccess: () => void;
    onCancel: () => void;
}

export const ConfigurationForm = ({
    category,
    providerName,
    displayName,
    logoUrl,
    configId,
    accountId,
    onSuccess,
    onCancel
}: ConfigurationFormProps) => {
    const [schema, setSchema] = useState<ProviderSchema | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isTesting, setIsTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const { toast } = useToast();

    const {
        control,
        handleSubmit,
        reset,
        watch,
        formState: { isSubmitting, errors, isValid }
    } = useForm({
        mode: 'onChange'
    });

    const formValues = watch();

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            try {
                const [schemaData, initialValues] = await Promise.all([
                    adminService.getProviderSchema(category, providerName),
                    configId ? adminService.getConfigValues(configId) : Promise.resolve({})
                ]);
                setSchema(schemaData as ProviderSchema);
                reset(initialValues);
            } catch {
                console.error("Failed to load configuration data");
                toast({
                    title: "Error",
                    description: "Failed to load provider configuration schema.",
                    variant: "destructive"
                });
            } finally {
                setIsLoading(false);
            }
        };

        loadData();
    }, [category, providerName, configId, reset, toast]);

    const onSubmit = async (values: Record<string, unknown>) => {
        try {
            if (configId) {
                await adminService.updateConfigValues(configId, values);
                toast({
                    title: "Success",
                    description: "Configuration updated successfully."
                });
            } else {
                await adminService.createConfig({
                    category,
                    provider_name: providerName,
                    display_name: displayName,
                    config: values,
                    account_id: accountId,
                    enabled: true
                });
                toast({
                    title: "Success",
                    description: "Configuration created successfully."
                });
            }
            onSuccess();
        } catch {
            toast({
                title: "Error",
                description: "Failed to save configuration.",
                variant: "destructive"
            });
        }
    };

    const handleTestConnection = async () => {
        setIsTesting(true);
        setTestResult(null);
        try {
            // Filter out masked secrets that weren't changed if needed? 
            // The handleTestConnection should probably pass the actual values.
            // If the user hasn't changed a secret, it will be "••••••••".
            // The backend updateConfigValues handles this, but test-connection might need it too.
            // However, the test-connection endpoint in backend DOES NOT have access to current DB config.
            // So if it sees "••••••••", it will fail.
            // THIS IS A KNOWN LIMITATION for testing EXISTING configs with secrets.
            // We should warn the user or handle it.

            const result = await adminService.testConnection({
                category,
                provider_name: providerName,
                config: formValues
            });
            setTestResult(result);
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setTestResult({
                success: false,
                message: err.response?.data?.detail || "Connection test failed."
            });
        } finally {
            setIsTesting(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const properties = schema?.properties || {};
    const requiredFields = schema?.required || [];

    // Check if any required field is still masked or empty
    const hasMaskedSecret = Object.entries(formValues).some(
        ([key, val]) => requiredFields.includes(key) && val === "••••••••"
    );

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col h-full overflow-hidden">
            <div className="px-6 py-4 border-b bg-muted/30">
                <div className="flex items-center gap-4">
                    <ProviderLogo
                        logoUrl={logoUrl}
                        providerName={providerName}
                        className="h-10 w-10 text-primary"
                        size={40}
                    />
                    <div className="flex flex-col">
                        <h3 className="text-lg font-semibold leading-none">{displayName}</h3>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground font-mono">{providerName}</span>
                            <Badge variant="secondary" className="text-[10px] h-4 px-1.5 uppercase">
                                {category.replace('_', ' ')}
                            </Badge>
                        </div>
                    </div>
                </div>
            </div>
            <ScrollArea className="flex-1 overflow-y-auto px-6 py-4">
                <div className="space-y-6">
                    {Object.entries(properties).map(([key, prop]) => {
                        const isRequired = requiredFields.includes(key);
                        const isSecret = prop.writeOnly || prop.format === 'password' || key.toLowerCase().includes('secret') || key.toLowerCase().includes('key');

                        return (
                            <Field key={key}>
                                <FieldLabel className="flex items-center gap-2">
                                    {prop.title || key}
                                    {isRequired && <span className="text-destructive">*</span>}
                                    {isSecret && <Lock className="h-3 w-3 text-muted-foreground" />}
                                </FieldLabel>
                                <FieldContent>
                                    <Controller
                                        name={key}
                                        control={control}
                                        rules={{ required: isRequired }}
                                        render={({ field }) => {
                                            if (prop.type === 'boolean') {
                                                return (
                                                    <div className="flex items-center space-x-2">
                                                        <Switch
                                                            checked={field.value}
                                                            onCheckedChange={field.onChange}
                                                        />
                                                        <span className="text-sm text-muted-foreground">
                                                            {field.value ? 'Enabled' : 'Disabled'}
                                                        </span>
                                                    </div>
                                                );
                                            }
                                            if (prop.enum) {
                                                return (
                                                    <Select
                                                        onValueChange={field.onChange}
                                                        value={field.value || prop.default || ""}
                                                    >
                                                        <SelectTrigger className="w-full">
                                                            <SelectValue placeholder={`Select ${prop.title || key}`} />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {prop.enum.map((option: string) => (
                                                                <SelectItem key={option} value={option}>
                                                                    {option}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                );
                                            }
                                            if (prop.type === 'array') {
                                                return (
                                                    <TagInput
                                                        value={field.value || prop.default || []}
                                                        onValueChange={field.onChange}
                                                        placeholder={prop.description || "Enter values..."}
                                                    />
                                                );
                                            }
                                            if (prop.type === 'number' || prop.type === 'integer') {
                                                return (
                                                    <Input
                                                        {...field}
                                                        type="number"
                                                        placeholder={prop.description}
                                                    />
                                                );
                                            }
                                            return (
                                                <Input
                                                    {...field}
                                                    type={isSecret ? "password" : "text"}
                                                    placeholder={prop.description}
                                                />
                                            );
                                        }}
                                    />
                                    <FieldError errors={[errors[key]]} />
                                </FieldContent>
                            </Field>
                        );
                    })}
                </div>
            </ScrollArea>

            <div className="p-6 border-t bg-background mt-auto">
                {testResult && (
                    <Alert variant={testResult.success ? "default" : "destructive"} className="mb-4">
                        {testResult.success ? (
                            <CheckCircle2 className="h-4 w-4" />
                        ) : (
                            <XCircle className="h-4 w-4" />
                        )}
                        <AlertTitle>{testResult.success ? "Connection Successful" : "Connection Failed"}</AlertTitle>
                        <AlertDescription>{testResult.message}</AlertDescription>
                    </Alert>
                )}

                {hasMaskedSecret && (
                    <p className="text-xs text-muted-foreground mb-4 italic">
                        Note: Connection testing may fail if secrets are masked. Please re-enter secrets to test.
                    </p>
                )}

                <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={handleTestConnection}
                        disabled={isTesting || isSubmitting || !isValid}
                    >
                        {isTesting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Testing...
                            </>
                        ) : (
                            "Test Connection"
                        )}
                    </Button>
                    <div className="flex flex-col-reverse sm:flex-row gap-3">
                        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {configId ? "Save Changes" : "Create Configuration"}
                        </Button>
                    </div>
                </div>
            </div>
        </form>
    );
};
