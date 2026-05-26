import { Info } from 'lucide-react';
import { EmptyState } from '@/components/common/empty-state';
import { Button, Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui';

export function DevicesPage() {
  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-card)] border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 p-4 text-sm text-[color:var(--warning)]">
        Device list is derived from OTA check audit logs. Connect an audit log endpoint to populate this view.
      </div>

      <Card>
        <CardContent className="pt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>MAC Address</TableHead>
                <TableHead>Device Type</TableHead>
                <TableHead>Current Version</TableHead>
                <TableHead>Last Seen</TableHead>
                <TableHead>Last Check Result</TableHead>
                <TableHead>Total Checks</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={7}>
                  <div className="space-y-4 py-6">
                    <EmptyState
                      icon={Info}
                      title="Audit endpoint required"
                      description="No device data is available until audit records can be fetched."
                    />
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button size="sm" variant="secondary" disabled>
                            Override
                          </Button>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>Available when audit data is connected</TooltipContent>
                    </Tooltip>
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
