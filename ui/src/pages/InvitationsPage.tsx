/**
 * Invitations management page
 * Manage user invitations
 */

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    RefreshCw,
    Mail,
    Copy,
    Trash2,
    CheckCircle2,
    AlertTriangle,
    XCircle,
    Clock,
    Send
} from 'lucide-react';
import {
    getInvitations,
    resendInvitation,
    cancelInvitation,
    type Invitation
} from '@/services/invitations.service';
import { getAccounts, type AccountListItem } from '@/services/accounts.service';
import { handleApiError } from '@/lib/api';
import { DataTable, type Column } from '@/components/common/DataTable';
import { useToast } from "@/hooks/use-toast";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { CreateInvitationDialog } from '@/components/invitations/CreateInvitationDialog';

export default function InvitationsPage() {
    const { toast } = useToast();
    const [data, setData] = useState<Invitation[] | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [isCreateOpen, setIsCreateOpen] = useState(false);

    const [accounts, setAccounts] = useState<AccountListItem[]>([]);
    const [loadingAccounts, setLoadingAccounts] = useState(false);
    const [showAccountFilter, setShowAccountFilter] = useState(false);
    const [accountFilter, setAccountFilter] = useState<string>('all');

    useEffect(() => {
        const loadAccounts = async () => {
            try {
                setLoadingAccounts(true);
                const response = await getAccounts({ page_size: 100 });
                if (response.items && response.items.length > 0) {
                    setAccounts(response.items);
                    setShowAccountFilter(true);
                }
            } catch (error) {
                // Ignore error - likely not superadmin
                console.debug("Failed to load accounts for filter", error);
            } finally {
                setLoadingAccounts(false);
            }
        };
        loadAccounts();
    }, []);

    const fetchInvitations = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const filter = statusFilter !== 'all' ? statusFilter : undefined;
            const acctFilter = accountFilter !== 'all' ? accountFilter : undefined;
            const response = await getInvitations(filter, acctFilter);
            setData(response.invitations);
            setTotal(response.total);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    }, [statusFilter, accountFilter]);

    useEffect(() => {
        fetchInvitations();
    }, [fetchInvitations]);

    const handleResend = async (id: string) => {
        try {
            await resendInvitation(id);
            toast({
                title: "Success",
                description: "Invitation email resent successfully",
            });
            await fetchInvitations();
        } catch (err) {
            toast({
                variant: "destructive",
                title: "Error",
                description: handleApiError(err),
            });
        }
    };

    const handleCopyLink = async (token: string) => {
        try {
            // Construct URL based on current origin
            const url = `${window.location.origin}/accept-invitation?token=${token}`;
            await navigator.clipboard.writeText(url);
            toast({
                title: "Copied",
                description: "Invitation link copied to clipboard",
            });
        } catch (err) {
            toast({
                variant: "destructive",
                title: "Error",
                description: "Failed to copy link",
            });
        }
    };

    const handleCancel = async (id: string) => {
        if (!confirm('Are you sure you want to cancel this invitation?')) return;

        try {
            await cancelInvitation(id);
            toast({
                title: "Success",
                description: "Invitation cancelled successfully",
            });
            await fetchInvitations();
        } catch (err) {
            toast({
                variant: "destructive",
                title: "Error",
                description: handleApiError(err),
            });
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'accepted':
                return <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50"><CheckCircle2 className="w-3 h-3 mr-1" /> Accepted</Badge>;
            case 'expired':
                return <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50"><XCircle className="w-3 h-3 mr-1" /> Expired</Badge>;
            case 'cancelled':
                return <Badge variant="outline" className="text-gray-600 border-gray-200 bg-gray-50"><XCircle className="w-3 h-3 mr-1" /> Cancelled</Badge>;
            default:
                return <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50"><Clock className="w-3 h-3 mr-1" /> Pending</Badge>;
        }
    };

    const columns: Column<Invitation>[] = [
        {
            header: 'Account',
            accessorKey: 'account_code',
            className: 'font-medium w-24',
            render: (inv) => <span className="text-sm font-mono text-muted-foreground">{inv.account_code || "Unknown"}</span>
        },
        {
            header: 'Email',
            accessorKey: 'email',
            className: 'font-medium'
        },
        {
            header: 'Status',
            render: (inv) => getStatusBadge(inv.status)
        },
        {
            header: 'Email Sent',
            render: (inv) => (
                inv.email_sent ?
                    <div className="flex items-center text-green-600 text-sm"><CheckCircle2 className="w-4 h-4 mr-1" /> Sent</div> :
                    <div className="flex items-center text-amber-600 text-sm"><AlertTriangle className="w-4 h-4 mr-1" /> Failed</div>
            )
        },
        {
            header: 'Expires',
            render: (inv) => <span className="text-sm text-muted-foreground">{new Date(inv.expires_at).toLocaleDateString()}</span>
        },
        {
            header: 'Actions',
            className: 'text-right',
            render: (inv) => (
                <div className="flex justify-end gap-2">
                    {inv.status === 'pending' && (
                        <>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => { e.stopPropagation(); handleResend(inv.id); }}
                                title="Resend Email"
                                className="text-blue-600 hover:text-blue-700"
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => { e.stopPropagation(); handleCopyLink(inv.token); }}
                                title="Copy Link"
                            >
                                <Copy className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => { e.stopPropagation(); handleCancel(inv.id); }}
                                title="Cancel Invitation"
                                className="text-destructive hover:text-destructive"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </>
                    )}
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6">
            <CreateInvitationDialog
                open={isCreateOpen}
                onOpenChange={setIsCreateOpen}
                onSuccess={() => {
                    fetchInvitations();
                }}
            />

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Invitations</h1>
                    <p className="text-muted-foreground mt-2">Manage team invitations</p>
                </div>
                <Button onClick={() => setIsCreateOpen(true)}>
                    <Mail className="mr-2 h-4 w-4" />
                    Invite User
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-primary" />
                        Invitation Management
                    </CardTitle>
                    <CardDescription>
                        View and manage pending invitations
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">

                    {/* Filters */}
                    <div className="flex flex-wrap items-end gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="status">Status</Label>
                            <Select
                                value={statusFilter}
                                onValueChange={setStatusFilter}
                            >
                                <SelectTrigger id="status" className="w-32">
                                    <SelectValue placeholder="All" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All</SelectItem>
                                    <SelectItem value="pending">Pending</SelectItem>
                                    <SelectItem value="accepted">Accepted</SelectItem>
                                    <SelectItem value="expired">Expired</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {showAccountFilter && (
                            <div className="space-y-2">
                                <Label htmlFor="account">Account</Label>
                                <Select
                                    value={accountFilter}
                                    onValueChange={setAccountFilter}
                                    disabled={loadingAccounts}
                                >
                                    <SelectTrigger id="account" className="w-48">
                                        <SelectValue placeholder="All Accounts" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">All Accounts</SelectItem>
                                        {accounts.map((account) => (
                                            <SelectItem key={account.id} value={account.id}>
                                                {account.name} ({account.account_code})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        <div className="ml-auto">
                            <Button variant="outline" size="icon" onClick={fetchInvitations} disabled={loading}>
                                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            </Button>
                        </div>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load invitations</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchInvitations} className="mt-4" size="sm">
                                Try Again
                            </Button>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && !data && (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    )}

                    {/* Table */}
                    {!loading && data && data.length === 0 && (
                        <div className="text-center py-12">
                            <Mail className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No invitations found</h3>
                            <Button variant="outline" onClick={() => setIsCreateOpen(true)}>
                                Invite your first user
                            </Button>
                        </div>
                    )}

                    {!loading && data && data.length > 0 && (
                        <DataTable
                            data={data}
                            columns={columns}
                            keyExtractor={(inv) => inv.id}
                            totalItems={total}
                            pagination={undefined} // Pagination not implemented in backend list yet (PRD F5.3 didn't specify, but list endpoint returns all)
                        />
                    )}

                </CardContent>
            </Card>
        </div>
    );
}
