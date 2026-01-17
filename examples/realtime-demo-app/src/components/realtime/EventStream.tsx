import { useEffect, useRef, useState } from 'react';
import { Plus, Edit, Trash, Clock, User, Zap } from 'lucide-react';
import { useRealtimeStore } from '../../stores/realtime.store';
import { cn } from '../../lib/utils';

export function EventStream() {
    const { events: allEvents } = useRealtimeStore();
    const events = allEvents.slice(0, 50); // Show only 50 most recent
    const scrollRef = useRef<HTMLDivElement>(null);
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        if (!isPaused && scrollRef.current) {
            scrollRef.current.scrollTop = 0; // Newest at top
        }
    }, [events, isPaused]);

    if (events.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
                <Zap className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-lg font-medium">No events yet</p>
                <p className="text-sm">Trigger an action from the left panel to see it appear here in real-time.</p>
            </div>
        );
    }

    const getRelativeTime = (timestamp: string) => {
        const now = new Date();
        const then = new Date(timestamp);
        const diff = Math.floor((now.getTime() - then.getTime()) / 1000);

        if (diff < 5) return 'just now';
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        return then.toLocaleTimeString();
    };

    const getIcon = (type: string) => {
        if (type.includes('create')) return <Plus className="w-3.5 h-3.5" />;
        if (type.includes('update')) return <Edit className="w-3.5 h-3.5" />;
        if (type.includes('delete')) return <Trash className="w-3.5 h-3.5" />;
        return <Zap className="w-3.5 h-3.5" />;
    };

    const getColor = (type: string) => {
        if (type.includes('create')) return 'text-green-600 bg-green-50 dark:bg-green-900/30 dark:text-green-400 border-green-100 dark:border-green-800';
        if (type.includes('update')) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400 border-blue-100 dark:border-blue-800';
        if (type.includes('delete')) return 'text-red-600 bg-red-50 dark:bg-red-900/30 dark:text-red-400 border-red-100 dark:border-red-800';
        return 'text-slate-600 bg-slate-50 dark:bg-slate-900/30 dark:text-slate-400 border-slate-100 dark:border-slate-800';
    };

    return (
        <div className="flex-1 overflow-hidden flex flex-col relative">
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"
            >
                {events.map((event, i) => {
                    const payload = event.data || {};
                    const opType = event.type || payload.type || 'unknown';

                    return (
                        <div
                            key={`${event.timestamp}-${i}`}
                            className="group animate-in fade-in slide-in-from-top-4 duration-300"
                        >
                            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 transition-all">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className={cn(
                                                "flex items-center justify-center w-6 h-6 rounded-lg border",
                                                getColor(opType)
                                            )}>
                                                {getIcon(opType)}
                                            </span>
                                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                                                {payload.message || 'System Event'}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-4 text-xs text-slate-500 pl-8">
                                            <span className="flex items-center gap-1">
                                                <User className="w-3.5 h-3.5" />
                                                {payload.user_name || 'System'}
                                            </span>
                                            <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 font-medium">
                                                {payload.entity_type || 'system'}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="text-[10px] font-medium text-slate-400 flex items-center gap-1 shrink-0">
                                        <Clock className="w-3 h-3" />
                                        {getRelativeTime(event.timestamp)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="p-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-between">
                <p className="text-[10px] text-slate-500 font-medium">
                    Showing {events.length} most recent events
                </p>
                <button
                    onClick={() => setIsPaused(!isPaused)}
                    className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded transition-colors",
                        isPaused ? "bg-orange-100 text-orange-700 dark:bg-orange-900/40" : "bg-blue-100 text-blue-700 dark:bg-blue-900/40"
                    )}
                >
                    {isPaused ? 'Paused' : 'Live Syncing'}
                </button>
            </div>
        </div>
    );
}
