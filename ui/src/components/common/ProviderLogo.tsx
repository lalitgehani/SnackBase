import React from 'react';
import { Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProviderLogoProps {
    logoUrl?: string | null;
    providerName: string;
    className?: string;
    size?: number | string;
}

export const ProviderLogo: React.FC<ProviderLogoProps> = ({
    logoUrl,
    providerName,
    className,
    size = 24,
}) => {
    const pixelSize = typeof size === 'number' ? `${size}px` : size;

    if (!logoUrl) {
        return (
            <div
                className={cn(
                    "bg-secondary rounded-full flex items-center justify-center shrink-0",
                    className
                )}
                style={{ width: pixelSize, height: pixelSize }}
            >
                <Settings style={{ width: `calc(${pixelSize} * 0.6)`, height: `calc(${pixelSize} * 0.6)` }} />
            </div>
        );
    }

    return (
        <div
            className={cn("shrink-0 bg-current", className)}
            style={{
                width: pixelSize,
                height: pixelSize,
                maskImage: `url(${logoUrl})`,
                maskRepeat: 'no-repeat',
                maskPosition: 'center',
                maskSize: 'contain',
                WebkitMaskImage: `url(${logoUrl})`,
                WebkitMaskRepeat: 'no-repeat',
                WebkitMaskPosition: 'center',
                WebkitMaskSize: 'contain',
            }}
            aria-label={`${providerName} logo`}
            role="img"
        />
    );
};
