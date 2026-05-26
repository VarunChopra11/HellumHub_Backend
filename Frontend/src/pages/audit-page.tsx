import { Info } from 'lucide-react';
import { EmptyState } from '@/components/common/empty-state';
import { Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui';

export function AuditPage() {
  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-secondary)]">
        Audit log endpoint not yet available. The backend stores audit records in the audit_checks collection. Expose GET
        /admin/audit to populate this view.
      </div>

      <Card>
        <CardContent className="pt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>MAC</TableHead>
                <TableHead>Device Type</TableHead>
                <TableHead>Current Version</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Chosen Version</TableHead>
                <TableHead>Request ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={7}>
                  <div className="py-6">
                    <EmptyState
                      icon={Info}
                      title="No audit entries"
                      description="Wire GET /admin/audit to instantly activate this table with color-coded result badges."
                    />
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
