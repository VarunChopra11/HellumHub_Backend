import { Skeleton } from '@/components/ui';

interface TableSkeletonProps {
  columns: number;
  rows?: number;
}

export function TableSkeleton({ columns, rows = 6 }: TableSkeletonProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`skeleton-row-${rowIndex}`} className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
          {Array.from({ length: columns }).map((__, colIndex) => (
            <Skeleton key={`skeleton-cell-${rowIndex}-${colIndex}`} className="h-8" />
          ))}
        </div>
      ))}
    </div>
  );
}
