/**
 * Table component for displaying SQL macros
 */

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MoreHorizontal, Edit, Trash2, Eye, Terminal } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Macro } from "@/types/macro"
import { format } from "date-fns"

interface MacrosTableProps {
    macros: Macro[]
    onView: (macro: Macro) => void
    onEdit: (macro: Macro) => void
    onDelete: (macro: Macro) => void
    onTest: (macro: Macro) => void
}

export default function MacrosTable({
    macros,
    onView,
    onEdit,
    onDelete,
    onTest,
}: MacrosTableProps) {

    const getParamCount = (paramsStr: string) => {
        try {
            const params = JSON.parse(paramsStr)
            return Array.isArray(params) ? params.length : 0
        } catch {
            return 0
        }
    }

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="text-center">Parameters</TableHead>
                        <TableHead>Last Updated</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {macros.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={5} className="h-24 text-center">
                                No macros found.
                            </TableCell>
                        </TableRow>
                    ) : (
                        macros.map((macro) => (
                            <TableRow key={macro.id}>
                                <TableCell className="font-medium">
                                    <div className="flex items-center gap-2">
                                        <span className="text-primary">@</span>
                                        {macro.name}
                                    </div>
                                </TableCell>
                                <TableCell className="max-w-xs truncate" title={macro.description || ""}>
                                    {macro.description || <span className="text-muted-foreground italic text-xs">No description</span>}
                                </TableCell>
                                <TableCell className="text-center">
                                    <Badge variant="secondary">
                                        {getParamCount(macro.parameters)}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    {format(new Date(macro.updated_at), "MMM d, yyyy HH:mm")}
                                </TableCell>
                                <TableCell className="text-right">
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                <span className="sr-only">Open menu</span>
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                            <DropdownMenuItem onClick={() => onView(macro)}>
                                                <Eye className="mr-2 h-4 w-4" />
                                                View Details
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => onTest(macro)}>
                                                <Terminal className="mr-2 h-4 w-4" />
                                                Test Macro
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem onClick={() => onEdit(macro)}>
                                                <Edit className="mr-2 h-4 w-4" />
                                                Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={() => onDelete(macro)}
                                                className="text-destructive focus:text-destructive"
                                            >
                                                <Trash2 className="mr-2 h-4 w-4" />
                                                Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
