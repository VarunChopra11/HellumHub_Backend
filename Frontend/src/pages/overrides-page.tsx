import { useMemo, useState } from 'react';
import { CircleAlert, Plus } from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui';
import { EmptyState } from '@/components/common/empty-state';
import { TableSkeleton } from '@/components/common/table-skeleton';
import { useDeleteOverride, useOverrides, useUpsertOverride } from '@/hooks/useOverrides';
import { formatRelativeTime } from '@/lib/formatRelativeTime';
import { normalizeMac } from '@/lib/validateMac';
import { validateSemver } from '@/lib/validateSemver';
import type { Override } from '@/types';

interface OverrideForm {
  device_type: string;
  mac: string;
  version: string;
  reason: string;
}

const initialForm: OverrideForm = {
  device_type: 'smart_switch',
  mac: '',
  version: '',
  reason: '',
};

function truncate(value: string | null, max = 40): string {
  if (!value) {
    return '-';
  }
  return value.length <= max ? value : `${value.slice(0, max)}...`;
}

export function OverridesPage() {
  const [deviceType, setDeviceType] = useState('smart_switch');
  const [draftDeviceType, setDraftDeviceType] = useState('smart_switch');
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState<Override | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [form, setForm] = useState<OverrideForm>(initialForm);

  const overridesQuery = useOverrides(deviceType);
  const upsertMutation = useUpsertOverride();
  const deleteMutation = useDeleteOverride(deviceType);

  const normalizedMac = useMemo(() => normalizeMac(form.mac), [form.mac]);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...initialForm, device_type: deviceType });
    setSheetOpen(true);
  };

  const openEdit = (entry: Override) => {
    setEditing(entry);
    setForm({
      device_type: entry.device_type,
      mac: entry.mac,
      version: entry.version,
      reason: entry.reason ?? '',
    });
    setSheetOpen(true);
  };

  const submitDisabled = !form.device_type.trim() || !normalizedMac || !validateSemver(form.version) || form.reason.length > 300;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input value={draftDeviceType} onChange={(event) => setDraftDeviceType(event.target.value)} className="sm:w-72" />
          <Button variant="secondary" onClick={() => setDeviceType(draftDeviceType.trim() || 'smart_switch')}>
            Apply
          </Button>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          New Override
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Overrides</CardTitle>
        </CardHeader>
        <CardContent>
          {overridesQuery.isLoading ? (
            <TableSkeleton columns={6} />
          ) : (overridesQuery.data?.length ?? 0) === 0 ? (
            <EmptyState
              icon={CircleAlert}
              title="No overrides"
              description="Create an override to pin a specific firmware version for a device MAC."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>MAC Address</TableHead>
                  <TableHead>Device Type</TableHead>
                  <TableHead>Pinned Version</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Updated At</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(overridesQuery.data ?? []).map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-mono text-xs">{entry.mac}</TableCell>
                    <TableCell>{entry.device_type}</TableCell>
                    <TableCell>{entry.version}</TableCell>
                    <TableCell>
                      {entry.reason ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>{truncate(entry.reason)}</span>
                          </TooltipTrigger>
                          <TooltipContent>{entry.reason}</TooltipContent>
                        </Tooltip>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell className="text-[var(--text-secondary)]">{formatRelativeTime(entry.updated_at)}</TableCell>
                    <TableCell>
                      {pendingDeleteId === entry.id ? (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[var(--text-secondary)]">Delete override for {entry.mac}?</span>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={deleteMutation.isPending}
                            onClick={() => {
                              deleteMutation.mutate({ mac: entry.mac });
                              setPendingDeleteId(null);
                            }}
                          >
                            Confirm
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => setPendingDeleteId(null)}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <Button size="sm" variant="secondary" onClick={() => openEdit(entry)}>
                            Edit
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setPendingDeleteId(entry.id)}>
                            Delete
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{editing ? 'Edit Override' : 'New Override'}</SheetTitle>
            <SheetDescription>Create or update a per-device firmware pin.</SheetDescription>
          </SheetHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (submitDisabled || !normalizedMac) {
                return;
              }

              upsertMutation.mutate(
                {
                  deviceType: form.device_type.trim(),
                  mac: normalizedMac,
                  version: form.version,
                  reason: form.reason.trim() ? form.reason.trim() : null,
                },
                {
                  onSuccess: () => {
                    setSheetOpen(false);
                    setEditing(null);
                    setForm({ ...initialForm, device_type: deviceType });
                  },
                },
              );
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="override-device-type">Device Type</Label>
              <Input
                id="override-device-type"
                value={form.device_type}
                onChange={(event) => setForm((curr) => ({ ...curr, device_type: event.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="override-mac">MAC Address</Label>
              <Input
                id="override-mac"
                value={form.mac}
                onChange={(event) => setForm((curr) => ({ ...curr, mac: event.target.value }))}
                placeholder="AA:BB:CC:DD:EE:FF"
              />
              <p className="text-xs text-[var(--text-secondary)]">
                Normalized: <span className="font-mono">{normalizedMac ?? 'Invalid MAC format'}</span>
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="override-version">Version</Label>
              <Input
                id="override-version"
                value={form.version}
                onChange={(event) => setForm((curr) => ({ ...curr, version: event.target.value }))}
              />
              {form.version && !validateSemver(form.version) ? (
                <p className="text-xs text-[var(--error)]">Invalid semver format.</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="override-reason">Reason (optional)</Label>
              <Input
                id="override-reason"
                value={form.reason}
                onChange={(event) => setForm((curr) => ({ ...curr, reason: event.target.value }))}
                maxLength={300}
              />
              <p className="text-xs text-[var(--text-secondary)]">{form.reason.length}/300</p>
            </div>

            <Button type="submit" disabled={submitDisabled || upsertMutation.isPending}>
              {upsertMutation.isPending ? 'Saving...' : editing ? 'Save Changes' : 'Create Override'}
            </Button>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
