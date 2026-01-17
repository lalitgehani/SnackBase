import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Check } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface CopyToClipboardButtonProps {
    value: string;
    label?: string;
    className?: string;
}

export const CopyToClipboardButton = ({ value, label, className }: CopyToClipboardButtonProps) => {
    const [copied, setCopied] = useState(false);
    const { toast } = useToast();

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(value);
            setCopied(true);
            toast({
                title: label ? `${label} copied` : 'Copied to clipboard',
                variant: 'default',
            });
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            toast({
                title: 'Failed to copy',
                description: 'Please try selecting and copying manually.',
                variant: 'destructive',
            });
        }
    };

    return (
        <Button
            variant="ghost"
            size="sm"
            className={className}
            onClick={handleCopy}
        >
            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
        </Button>
    );
};
