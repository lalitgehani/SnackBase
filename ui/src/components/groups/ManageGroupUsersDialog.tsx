/**
 * Manage group users dialog component
 * Allows adding and removing users from a group
 */

import { useEffect, useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, UserPlus, UserMinus, Search } from 'lucide-react';
import type { Group } from '@/services/groups.service';
import { getUsers, type User } from '@/services/users.service';

interface ManageGroupUsersDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    group: Group | null;
    onAddUser: (groupId: string, userId: string) => Promise<void>;
    onRemoveUser: (groupId: string, userId: string) => Promise<void>;
}

export default function ManageGroupUsersDialog({
    open,
    onOpenChange,
    group,
    onAddUser,
    onRemoveUser,
}: ManageGroupUsersDialogProps) {
    const [users, setUsers] = useState<User[]>([]);
    const [groupUsers, setGroupUsers] = useState<User[]>([]);
    const [selectedUserId, setSelectedUserId] = useState('');
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load users when dialog opens
    useEffect(() => {
        if (open && group) {
            loadUsers();
        }
    }, [open, group]);

    const loadUsers = async () => {
        setLoadingUsers(true);
        try {
            // Fetch all users in account (for adding new members)
            const usersPromise = getUsers({
                account_id: group?.account_id,
                limit: 100,
            });

            // Fetch current group members (by getting full group details)
            // We use the imported getGroup from services which corresponds to the GET /groups/{id} endpoint
            // Dynamically import to avoid circular dependency if needed, or assume it's available
            const groupPromise = import('@/services/groups.service').then(m => m.getGroup(group!.id));

            const [usersResponse, groupDetails] = await Promise.all([
                usersPromise,
                groupPromise
            ]);

            setUsers(usersResponse.items);

            if (groupDetails && groupDetails.users) {
                setGroupUsers(groupDetails.users);
            } else {
                setGroupUsers([]);
            }
        } catch (err) {
            console.error('Failed to load users:', err);
        } finally {
            setLoadingUsers(false);
        }
    };

    const handleAddUser = async () => {
        if (!group || !selectedUserId) return;

        setLoading(true);
        setError(null);

        try {
            await onAddUser(group.id, selectedUserId);
            // Add user to local state
            const user = users.find((u) => u.id === selectedUserId);
            if (user) {
                setGroupUsers([...groupUsers, user]);
            }
            setSelectedUserId('');
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to add user';
            setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveUser = async (userId: string) => {
        if (!group) return;

        setLoading(true);
        setError(null);

        try {
            await onRemoveUser(group.id, userId);
            // Remove user from local state
            setGroupUsers(groupUsers.filter((u) => u.id !== userId));
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to remove user';
            setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        } finally {
            setLoading(false);
        }
    };

    // Filter available users (exclude those already in group)
    const availableUsers = users.filter(
        (user) =>
            !groupUsers.some((gu) => gu.id === user.id) &&
            (searchTerm === '' || user.email.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Manage Group Members</DialogTitle>
                    <DialogDescription>
                        Add or remove users from <strong>{group?.name}</strong>
                    </DialogDescription>
                </DialogHeader>

                {loadingUsers ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <div className="space-y-6 py-4">
                        {/* Current Members */}
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <Label className="text-base font-semibold">Current Members</Label>
                                <Badge variant="secondary">{groupUsers.length} members</Badge>
                            </div>

                            {groupUsers.length === 0 ? (
                                <div className="text-center py-6 bg-muted rounded-lg">
                                    <p className="text-sm text-muted-foreground">No members yet</p>
                                </div>
                            ) : (
                                <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                                    {groupUsers.map((user) => (
                                        <div
                                            key={user.id}
                                            className="flex items-center justify-between p-2 hover:bg-muted rounded-md"
                                        >
                                            <div>
                                                <p className="font-medium">{user.email}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {user.role_name} • {user.is_active ? 'Active' : 'Inactive'}
                                                </p>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleRemoveUser(user.id)}
                                                disabled={loading}
                                                className="text-destructive hover:text-destructive"
                                            >
                                                <UserMinus className="h-4 w-4 mr-1" />
                                                Remove
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Add Members */}
                        <div className="space-y-3">
                            <Label className="text-base font-semibold">Add Members</Label>

                            <div className="space-y-2">
                                <div className="relative">
                                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        placeholder="Search users by email..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="pl-8"
                                    />
                                </div>

                                <div className="flex gap-2">
                                    <Select
                                        value={selectedUserId}
                                        onValueChange={setSelectedUserId}
                                        disabled={loading || availableUsers.length === 0}
                                    >
                                        <SelectTrigger className="flex-1">
                                            <SelectValue placeholder="Select a user to add" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {availableUsers.map((user) => (
                                                <SelectItem key={user.id} value={user.id}>
                                                    {user.email} ({user.role_name})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <Button
                                        onClick={handleAddUser}
                                        disabled={loading || !selectedUserId}
                                    >
                                        {loading ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <>
                                                <UserPlus className="h-4 w-4 mr-1" />
                                                Add
                                            </>
                                        )}
                                    </Button>
                                </div>

                                {availableUsers.length === 0 && (
                                    <p className="text-sm text-muted-foreground">
                                        {searchTerm
                                            ? 'No users found matching your search'
                                            : 'All users in this account are already members'}
                                    </p>
                                )}
                            </div>
                        </div>

                        {error && (
                            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                                {error}
                            </div>
                        )}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
