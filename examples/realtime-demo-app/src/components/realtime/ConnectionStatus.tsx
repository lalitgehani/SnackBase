import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { useRealtimeStore } from '../../stores/realtime.store';
import { cn } from '../../lib/utils';

export function ConnectionStatus() {
    const { connectionState, isSubscribed, error } = useRealtimeStore();

    const statusConfig = {
        connected: {
            color: 'bg-green-500',
            text: 'Connected',
            icon: <Wifi className="w-4 h-4" />,
        },
        connecting: {
            color: 'bg-yellow-500',
            text: 'Connecting...',
            icon: <Loader2 className="w-4 h-4 animate-spin" />,
        },
        disconnected: {
            color: 'bg-slate-400',
            text: 'Disconnected',
            icon: <WifiOff className="w-4 h-4" />,
        },
        error: {
            color: 'bg-red-500',
            text: 'Connection Error',
            icon: <AlertCircle className="w-4 h-4" />,
        },
    };

    const current = statusConfig[connectionState];

    return (
        <div className="flex items-center gap-4">
            {isSubscribed && connectionState === 'connected' && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
                    Subscribed
                </span>
            )}

            <div className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium transition-colors",
                connectionState === 'connected' ? "bg-green-50 border-green-200 text-green-700 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400" :
                    connectionState === 'connecting' ? "bg-yellow-50 border-yellow-200 text-yellow-700 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-400" :
                        connectionState === 'error' ? "bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400" :
                            "bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-900/20 dark:border-slate-800 dark:text-slate-400"
            )}>
                <div className={cn("w-2 h-2 rounded-full", current.color, connectionState === 'connecting' && "animate-pulse")} />
                <span className="hidden sm:inline">{current.text}</span>
                {current.icon}
            </div>

            {error && connectionState === 'error' && (
                <span className="text-xs text-red-500 max-w-[150px] truncate hidden md:inline" title={error}>
                    {error}
                </span>
            )}
        </div>
    );
}
