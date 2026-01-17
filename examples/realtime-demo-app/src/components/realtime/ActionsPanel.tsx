import React, { useState } from 'react';
import { Plus, Edit, Trash, Send, Loader2, CheckCircle2 } from 'lucide-react';
import { activitiesService } from '../../services/activities.service';
import { cn } from '../../lib/utils';
import type { ActivityType, CreateActivity } from '../../types';

export function ActionsPanel() {
    const [loading, setLoading] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [formData, setFormData] = useState<CreateActivity>({
        type: 'create',
        entity_type: 'post',
        message: '',
        user_name: 'Demo User'
    });

    const quickActions = [
        { label: 'Create Post', type: 'create', entity: 'post', icon: <Plus className="w-4 h-4" /> },
        { label: 'Update Post', type: 'update', entity: 'post', icon: <Edit className="w-4 h-4" /> },
        { label: 'Delete Post', type: 'delete', entity: 'post', icon: <Trash className="w-4 h-4" /> },
        { label: 'New User', type: 'create', entity: 'user', icon: <Plus className="w-4 h-4 text-blue-500" /> },
        { label: 'New Comment', type: 'create', entity: 'comment', icon: <Plus className="w-4 h-4 text-purple-500" /> },
    ];

    const handleAction = async (type: ActivityType, entity: string, label: string) => {
        setLoading(label);
        try {
            await activitiesService.createActivity({
                type,
                entity_type: entity,
                message: `${label} triggered from demo`,
                user_name: 'Demo User'
            });
            showSuccess(label);
        } catch (error) {
            console.error('Action failed', error);
        } finally {
            setLoading(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.message) return;

        setLoading('manual');
        try {
            await activitiesService.createActivity(formData);
            showSuccess('Custom Activity');
            setFormData({ ...formData, message: '' });
        } catch (error) {
            console.error('Submission failed', error);
        } finally {
            setLoading(null);
        }
    };

    const showSuccess = (label: string) => {
        setSuccess(label);
        setTimeout(() => setSuccess(null), 2000);
    };

    return (
        <div className="space-y-8">
            {/* Quick Actions */}
            <div className="space-y-4">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Quick Actions</h3>
                <div className="flex flex-wrap gap-2">
                    {quickActions.map((action) => (
                        <button
                            key={action.label}
                            onClick={() => handleAction(action.type as ActivityType, action.entity, action.label)}
                            disabled={loading !== null}
                            className={cn(
                                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all active:scale-95 disabled:opacity-50 disabled:active:scale-100",
                                "bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 border border-transparent hover:border-slate-300 dark:hover:border-slate-600",
                                success === action.label && "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400"
                            )}
                        >
                            {loading === action.label ? <Loader2 className="w-4 h-4 animate-spin" /> :
                                success === action.label ? <CheckCircle2 className="w-4 h-4" /> : action.icon}
                            {action.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-px bg-slate-200 dark:bg-slate-800" />

            {/* Manual Form */}
            <div className="space-y-4">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Custom Activity</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-slate-500">Operation</label>
                            <select
                                value={formData.type}
                                onChange={(e) => setFormData({ ...formData, type: e.target.value as ActivityType })}
                                className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                            >
                                <option value="create">Create</option>
                                <option value="update">Update</option>
                                <option value="delete">Delete</option>
                            </select>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-slate-500">Entity Type</label>
                            <input
                                type="text"
                                value={formData.entity_type}
                                onChange={(e) => setFormData({ ...formData, entity_type: e.target.value })}
                                placeholder="e.g. post, user"
                                className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-slate-500">Message</label>
                        <input
                            type="text"
                            required
                            value={formData.message}
                            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                            placeholder="What happened?"
                            className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                        />
                    </div>

                    <div className="flex gap-2">
                        <button
                            type="submit"
                            disabled={loading !== null || !formData.message}
                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2.5 text-sm font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98] disabled:opacity-70 disabled:active:scale-100"
                        >
                            {loading === 'manual' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            Send Activity
                        </button>
                        <button
                            type="button"
                            onClick={() => setFormData({ ...formData, message: '' })}
                            className="px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                        >
                            Clear
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
