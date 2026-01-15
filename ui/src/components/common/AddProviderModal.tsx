import { useState, useEffect } from 'react';
import { adminService, type Configuration, type AvailableProvider } from '@/services/admin.service';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ConfigurationForm } from './ConfigurationForm';
import { Loader2, ArrowLeft, BadgeCheck } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ProviderLogo } from '@/components/common/ProviderLogo';
import { useToast } from '@/hooks/use-toast';


// List of providers that have been manually tested and verified
const VERIFIED_PROVIDERS = ['google'];

interface AddProviderModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfigCreated: () => void;
    category?: string;
    accountId?: string;
    existingConfigs?: Configuration[];
}

export const AddProviderModal = ({
    open,
    onOpenChange,
    onConfigCreated,
    category,
    accountId,
    existingConfigs = [],
}: AddProviderModalProps) => {
    const [selectedProvider, setSelectedProvider] = useState<AvailableProvider | null>(null);
    const [availableProviders, setAvailableProviders] = useState<AvailableProvider[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        if (open) {
            const loadProviders = async () => {
                setIsLoading(true);
                try {
                    const data = await adminService.getAvailableProviders(category);
                    // Filter out already configured providers and explicitly exclude email_password
                    const filtered = data.filter(
                        (p: AvailableProvider) =>
                            p.provider_name !== "email_password" &&
                            !existingConfigs.some((ec) => ec.provider_name === p.provider_name) &&
                            // System settings are only applicable to system level (no accountId)
                            !(p.category === 'system_settings' && accountId)
                    );

                    setAvailableProviders(filtered);
                } catch (error) {
                    console.error("Failed to load providers", error);
                    toast({
                        title: "Error",
                        description: "Failed to load available providers.",
                        variant: "destructive",
                    });
                } finally {
                    setIsLoading(false);
                }
            };
            loadProviders();
            setSelectedProvider(null);
        }
    }, [open, category, existingConfigs, toast]);

    const handleSuccess = () => {
        onConfigCreated();
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-xl p-0 overflow-hidden flex flex-col h-162.5 max-h-[90vh]">
                <DialogHeader className="p-6 pb-0">
                    <div className="flex items-center gap-2">
                        {selectedProvider && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => setSelectedProvider(null)}
                            >
                                <ArrowLeft className="h-4 w-4" />
                            </Button>
                        )}
                        <DialogTitle>
                            {selectedProvider
                                ? `Configure ${selectedProvider.display_name}`
                                : 'Add Provider'}
                        </DialogTitle>
                    </div>
                    <DialogDescription>
                        {selectedProvider
                            ? `Fill in the details to set up ${selectedProvider.display_name}.`
                            : 'Select a provider to add to your configuration.'}
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-hidden h-full flex flex-col">
                    {isLoading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : selectedProvider ? (
                        <ConfigurationForm
                            category={selectedProvider.category}
                            providerName={selectedProvider.provider_name}
                            displayName={selectedProvider.display_name}
                            logoUrl={selectedProvider.logo_url}
                            accountId={accountId}
                            onSuccess={handleSuccess}
                            onCancel={() => setSelectedProvider(null)}
                        />
                    ) : (
                        <ScrollArea className="flex-1 px-6">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-4">
                                {availableProviders.map((p) => {
                                    const isVerified = VERIFIED_PROVIDERS.includes(p.provider_name);
                                    return (
                                        <Button
                                            key={`${p.category}:${p.provider_name}`}
                                            variant="outline"
                                            className="h-24 flex flex-col items-center justify-center gap-2 hover:border-primary hover:bg-primary/5 transition-all text-center p-4 relative"
                                            onClick={() => setSelectedProvider(p)}
                                        >
                                            {isVerified && (
                                                <div className="absolute top-2 right-2">
                                                    <BadgeCheck className="h-4 w-4 text-green-600 dark:text-green-500" />
                                                </div>
                                            )}
                                            <ProviderLogo
                                                logoUrl={p.logo_url}
                                                providerName={p.provider_name}
                                                className="h-8 w-8"
                                                size={32}
                                            />
                                            <div className="flex flex-col">
                                                <span className="font-medium text-sm line-clamp-1">{p.display_name}</span>
                                                <span className="text-[10px] text-muted-foreground uppercase">{p.category.replace('_', ' ')}</span>
                                            </div>
                                        </Button>
                                    );
                                })}
                                {availableProviders.length === 0 && (
                                    <div className="col-span-full py-12 text-center text-muted-foreground">
                                        No providers available for this category.
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};
