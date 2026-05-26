import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-[var(--radius-badge)] border px-2 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-[var(--border)] text-[var(--text-primary)] bg-transparent',
        success: 'border-[color:var(--success)]/30 bg-[color:var(--success)]/10 text-[color:var(--success)]',
        warning: 'border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 text-[color:var(--warning)]',
        error: 'border-[color:var(--error)]/30 bg-[color:var(--error)]/10 text-[color:var(--error)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
