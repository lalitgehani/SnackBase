import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { adminService } from '@/services/admin.service';
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

interface ConfigurationFormProps {
    category: string;
    providerName: string;
    displayName: string;
    configId?: string;
    accountId?: string;
    onSuccess: () => void;
    onCancel: () => void;
}

export const ConfigurationForm = ({
    category,
    providerName,
    displayName,
    configId,
    accountId,
    onSuccess,
    onCancel
}: ConfigurationFormProps) => {
    const [schema, setSchema] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isTesting, setIsTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const { toast } = useToast();

    const {
        control,
        handleSubmit,
        reset,
        watch,
        formState: { isSubmitting, errors }
    } = useForm();

    const formValues = watch();

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            try {
                const [schemaData, initialValues] = await Promise.all([
                    adminService.getProviderSchema(category, providerName),
                    configId ? adminService.getConfigValues(configId) : Promise.resolve({})
                ]);
                setSchema(schemaData);
                reset(initialValues);
            } catch (error) {
                console.error("Failed to load configuration data", error);
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

    const onSubmit = async (values: any) => {
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
        } catch (error) {
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
            const result = await adminService.testConnection({
                category,
                provider_name: providerName,
                config: formValues
            });
            setTestResult(result);
        } catch (error: any) {
            setTestResult({
                success: false,
                message: error.response?.data?.detail || "Connection test failed."
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

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col h-full overflow-hidden">
            <ScrollArea className="flex-1 overflow-y-auto px-6 py-4">
                <div className="space-y-6">
                    {Object.entries(properties).map(([key, prop]: [string, any]) => {
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

                <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={handleTestConnection}
                        disabled={isTesting || isSubmitting}
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
