import { useState } from 'react';
import { ActionsPanel } from './ActionsPanel';
import { EventStream } from './EventStream';
import { ConnectionStatus } from './ConnectionStatus';
import { useRealtimeStore } from '../../stores/realtime.store';
import { HelpCircle, ChevronDown, ChevronUp, Github, ExternalLink, LogOut, User } from 'lucide-react';

export function RealtimeDemo() {
    const [showInstructions, setShowInstructions] = useState(true);
    const { clearEvents, logout, user } = useRealtimeStore();

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50">
            <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-20">
                <div className="w-full px-6 h-16 flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold tracking-tight">SnackBase Realtime</h1>
                        <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">WebSocket Demo Application</p>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="hidden md:flex items-center gap-2 text-slate-500 bg-slate-50 dark:bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">
                            <User className="w-3.5 h-3.5" />
                            <span className="text-xs font-medium">{user?.email}</span>
                        </div>
                        <ConnectionStatus />
                        <button
                            onClick={() => logout()}
                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-lg transition-colors"
                            title="Sign Out"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </header>

            <main className="w-full px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Left Panel: Actions & Instructions */}
                    <div className="lg:col-span-4 space-y-6">
                        {/* Instructions Panel */}
                        <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                            <button
                                onClick={() => setShowInstructions(!showInstructions)}
                                className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    <HelpCircle className="w-4 h-4 text-blue-500" />
                                    <h2 className="text-sm font-bold uppercase tracking-wider">How to use this demo</h2>
                                </div>
                                {showInstructions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>

                            {showInstructions && (
                                <div className="px-6 pb-6 space-y-4 animate-in slide-in-from-top-2 duration-200">
                                    <div className="space-y-3">
                                        <div className="flex gap-3">
                                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-bold flex items-center justify-center">1</span>
                                            <p className="text-sm text-slate-600 dark:text-slate-400">Open this page in two separate browser tabs.</p>
                                        </div>
                                        <div className="flex gap-3">
                                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-bold flex items-center justify-center">2</span>
                                            <p className="text-sm text-slate-600 dark:text-slate-400">Click any action button in the panel below.</p>
                                        </div>
                                        <div className="flex gap-3">
                                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-bold flex items-center justify-center">3</span>
                                            <p className="text-sm text-slate-600 dark:text-slate-400">Watch the event appear in both tabs instantly via WebSockets.</p>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800/50">
                                        <p className="text-xs text-blue-700 dark:text-blue-300">
                                            <strong>Note:</strong> This demonstrates real-time synchronization across clients using SnackBase's subscription engine.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </section>

                        <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            <ActionsPanel />
                        </section>
                    </div>

                    {/* Right Panel: Event Stream */}
                    <div className="lg:col-span-8">
                        <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col h-[calc(100vh-14rem)] shadow-sm overflow-hidden">
                            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/20">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                    <h2 className="text-sm font-bold uppercase tracking-wider">Live Event Stream</h2>
                                </div>
                                <button
                                    onClick={() => clearEvents()}
                                    className="text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-colors"
                                >
                                    Clear Stream
                                </button>
                            </div>
                            <EventStream />
                        </section>
                    </div>
                </div>
            </main>

            <footer className="w-full px-6 py-12 flex flex-col md:flex-row items-center justify-between gap-6 border-t border-slate-200 dark:border-slate-800 mt-8">
                <div className="flex items-center gap-2 text-slate-500">
                    <span className="text-sm font-medium">Powered by</span>
                    <a
                        href="https://github.com/snackbase/snackbase"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-slate-900 dark:text-white font-bold hover:text-blue-600 transition-colors"
                    >
                        SnackBase
                        <ExternalLink className="w-3 h-3" />
                    </a>
                </div>

                <div className="flex items-center gap-8">
                    <a
                        href="https://github.com/snackbase/snackbase"
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                        title="GitHub Repository"
                    >
                        <Github className="w-5 h-5" />
                    </a>
                    <div className="text-center md:text-right">
                        <p className="text-xs text-slate-400">© 2025 SnackBase. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
