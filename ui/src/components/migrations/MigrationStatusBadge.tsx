import { Badge } from '@/components/ui/badge';
import { Check, Clock, Star } from 'lucide-react';

interface MigrationStatusBadgeProps {
    isApplied: boolean;
    isHead: boolean;
    isCurrent?: boolean;
}

export default function MigrationStatusBadge({
    isApplied,
    isHead,
    isCurrent = false,
}: MigrationStatusBadgeProps) {
    return (
        <div className="flex gap-1">
            {isApplied && (
                <Badge
                    variant="default"
                    className={`bg-green-500 hover:bg-green-600 ${isCurrent ? 'ring-2 ring-green-700' : ''}`}
                >
                    <Check className="h-3 w-3 mr-1" />
                    Applied
                </Badge>
            )}
            {!isApplied && (
                <Badge
                    variant="secondary"
                    className="bg-yellow-500 hover:bg-yellow-600 text-white"
                >
                    <Clock className="h-3 w-3 mr-1" />
                    Pending
                </Badge>
            )}
            {isHead && (
                <Badge
                    variant="default"
                    className="bg-blue-500 hover:bg-blue-600"
                >
                    <Star className="h-3 w-3 mr-1" />
                    Head
                </Badge>
            )}
        </div>
    );
}
