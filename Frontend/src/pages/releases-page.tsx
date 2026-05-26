import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { compare, rcompare } from 'semver';
import { CircleAlert, CloudUpload, Plus, RefreshCw, SlidersHorizontal } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Popover,
  PopoverContent,
  PopoverTrigger,
  Progress,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Slider,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui';
import { EmptyState } from '@/components/common/empty-state';
import { StatCard } from '@/components/common/stat-card';
import { TableSkeleton } from '@/components/common/table-skeleton';
import {
  useCreateRelease,
  useReleases,
  useToggleReleaseEnabled,
  useUpdateReleaseRollout,
  useUploadReleaseFirmware,
} from '@/hooks/useReleases';
import { formatRelativeTime } from '@/lib/formatRelativeTime';
import { validateSemver } from '@/lib/validateSemver';
import type { ApiError } from '@/lib/apiError';
import type { Release } from '@/types';

function truncate(value: string | null, max = 40): string {
  if (!value) {
    return '-';
  }
  return value.length <= max ? value : `${value.slice(0, max)}...`;
}

interface NewReleaseForm {
  device_type: string;
  version: string;
  rollout_percentage: number;
  enabled: boolean;
  notes: string;
}

export function ReleasesPage() {
  const navigate = useNavigate();
  const [deviceType, setDeviceType] = useState('smart_switch');
  const [draftDeviceType, setDraftDeviceType] = useState('smart_switch');
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<Release | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [rolloutDrafts, setRolloutDrafts] = useState<Record<string, number>>({});
  const [newReleaseForm, setNewReleaseForm] = useState<NewReleaseForm>({
    device_type: 'smart_switch',
    version: '',
    rollout_percentage: 100,
    enabled: false,
    notes: '',
  });

  const releasesQuery = useReleases(deviceType);
  const createReleaseMutation = useCreateRelease(deviceType);
  const toggleEnabledMutation = useToggleReleaseEnabled(deviceType);
  const updateRolloutMutation = useUpdateReleaseRollout(deviceType);
  const uploadFirmwareMutation = useUploadReleaseFirmware(deviceType);

  const releases = releasesQuery.data ?? [];

  const stats = useMemo(() => {
    const total = releases.length;
    const enabledCount = releases.filter((item) => item.enabled).length;
    const enabledVersions = releases.filter((item) => item.enabled).map((item) => item.version);
    const latestEnabled = enabledVersions.sort((a, b) => rcompare(a, b))[0] ?? '-';
    const totalSizeBytes = releases.reduce((sum, item) => sum + (item.size ?? 0), 0);

    return {
      total,
      enabledCount,
      latestEnabled,
      totalSizeMb: `${(totalSizeBytes / (1024 * 1024)).toFixed(2)} MB`,
    };
  }, [releases]);

  const versionValid = newReleaseForm.version.length === 0 || validateSemver(newReleaseForm.version);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
        <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center lg:w-auto">
          <Input
            value={draftDeviceType}
            onChange={(event) => setDraftDeviceType(event.target.value)}
            placeholder="device_type"
            className="sm:w-72"
          />
          <Button
            variant="secondary"
            onClick={() => {
              setDeviceType(draftDeviceType.trim() || 'smart_switch');
            }}
          >
            Apply
          </Button>
          <Button variant="secondary" onClick={() => releasesQuery.refetch()} disabled={releasesQuery.isFetching}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
        <Button onClick={() => setIsSheetOpen(true)}>
          <Plus className="h-4 w-4" />
          New Release
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Releases" value={stats.total} />
        <StatCard label="Enabled Releases" value={stats.enabledCount} />
        <StatCard label="Latest Enabled" value={stats.latestEnabled} />
        <StatCard label="Total Firmware Size" value={stats.totalSizeMb} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Releases</CardTitle>
        </CardHeader>
        <CardContent>
          {releasesQuery.isLoading ? (
            <TableSkeleton columns={8} />
          ) : releases.length === 0 ? (
            <EmptyState
              icon={CircleAlert}
              title="No releases yet"
              description="No releases yet. Create your first release to get started."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>Device Type</TableHead>
                  <TableHead>Rollout %</TableHead>
                  <TableHead>Firmware</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {releases
                  .slice()
                  .sort((a, b) => compare(b.version, a.version))
                  .map((release) => {
                    const rolloutValue = rolloutDrafts[release.id] ?? release.rollout_percentage;
                    return (
                      <TableRow key={release.id}>
                        <TableCell>
                          <Badge variant={release.enabled ? 'success' : 'default'}>{release.version}</Badge>
                        </TableCell>
                        <TableCell>{release.device_type}</TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <Progress value={release.rollout_percentage} />
                            <span className="text-xs text-[var(--text-secondary)]">{release.rollout_percentage}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {release.firmware_file_id ? (
                            <Badge variant="success">Uploaded</Badge>
                          ) : (
                            <Badge variant="error">Missing</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={release.enabled}
                            disabled={toggleEnabledMutation.isPending}
                            onCheckedChange={(checked) => {
                              toggleEnabledMutation.mutate({ releaseId: release.id, enabled: checked });
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          {release.notes ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="cursor-default text-sm">{truncate(release.notes)}</span>
                              </TooltipTrigger>
                              <TooltipContent>{release.notes}</TooltipContent>
                            </Tooltip>
                          ) : (
                            <span className="text-[var(--text-secondary)]">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-[var(--text-secondary)]">{formatRelativeTime(release.created_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Popover>
                              <PopoverTrigger asChild>
                                <Button size="sm" variant="secondary">
                                  <SlidersHorizontal className="h-3.5 w-3.5" />
                                  Edit rollout
                                </Button>
                              </PopoverTrigger>
                              <PopoverContent className="space-y-3">
                                <Label>Rollout Percentage</Label>
                                <Slider
                                  value={[rolloutValue]}
                                  min={0}
                                  max={100}
                                  step={1}
                                  onValueChange={(value) =>
                                    setRolloutDrafts((current) => ({ ...current, [release.id]: value[0] ?? 0 }))
                                  }
                                />
                                <p className="text-xs text-[var(--text-secondary)]">{rolloutValue}%</p>
                                <Button
                                  size="sm"
                                  disabled={updateRolloutMutation.isPending}
                                  onClick={() =>
                                    updateRolloutMutation.mutate({
                                      releaseId: release.id,
                                      rolloutPercentage: rolloutValue,
                                    })
                                  }
                                >
                                  Save
                                </Button>
                              </PopoverContent>
                            </Popover>

                            <Button size="sm" variant="secondary" onClick={() => setUploadTarget(release)}>
                              <CloudUpload className="h-3.5 w-3.5" />
                              Upload firmware
                            </Button>

                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() =>
                                navigate(`/releases/${release.id}?device_type=${encodeURIComponent(release.device_type)}`)
                              }
                            >
                              View detail
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Create Release</SheetTitle>
            <SheetDescription>Create a new firmware release record.</SheetDescription>
          </SheetHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!validateSemver(newReleaseForm.version)) {
                return;
              }

              createReleaseMutation.mutate(
                {
                  device_type: newReleaseForm.device_type,
                  version: newReleaseForm.version,
                  rollout_percentage: newReleaseForm.rollout_percentage,
                  enabled: newReleaseForm.enabled,
                  notes: newReleaseForm.notes.trim() ? newReleaseForm.notes.trim() : null,
                },
                {
                  onSuccess: () => {
                    setIsSheetOpen(false);
                    setNewReleaseForm({
                      device_type: deviceType,
                      version: '',
                      rollout_percentage: 100,
                      enabled: false,
                      notes: '',
                    });
                  },
                  onError: (error) => {
                    const typed = error as ApiError;
                    if (typed.status === 409) {
                      createReleaseMutation.reset();
                    }
                  },
                },
              );
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="new-release-device-type">Device Type</Label>
              <Input
                id="new-release-device-type"
                value={newReleaseForm.device_type}
                onChange={(event) => setNewReleaseForm((curr) => ({ ...curr, device_type: event.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-release-version">Version</Label>
              <Input
                id="new-release-version"
                value={newReleaseForm.version}
                onChange={(event) => setNewReleaseForm((curr) => ({ ...curr, version: event.target.value }))}
                className={!versionValid ? 'border-[var(--error)]' : ''}
              />
              {!versionValid ? <p className="text-xs text-[var(--error)]">Invalid semver format</p> : null}
            </div>

            <div className="space-y-2">
              <Label>Rollout Percentage</Label>
              <Slider
                value={[newReleaseForm.rollout_percentage]}
                min={0}
                max={100}
                step={1}
                onValueChange={(value) => setNewReleaseForm((curr) => ({ ...curr, rollout_percentage: value[0] ?? 0 }))}
              />
              <p className="text-xs text-[var(--text-secondary)]">{newReleaseForm.rollout_percentage}%</p>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="new-release-enabled">Enabled</Label>
              <Switch
                id="new-release-enabled"
                checked={newReleaseForm.enabled}
                onCheckedChange={(checked) => setNewReleaseForm((curr) => ({ ...curr, enabled: checked }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-release-notes">Notes</Label>
              <Textarea
                id="new-release-notes"
                value={newReleaseForm.notes}
                onChange={(event) => setNewReleaseForm((curr) => ({ ...curr, notes: event.target.value }))}
              />
            </div>

            {createReleaseMutation.error && (createReleaseMutation.error as ApiError).status === 409 ? (
              <p className="text-sm text-[var(--error)]">Version already exists</p>
            ) : null}

            <Button type="submit" disabled={createReleaseMutation.isPending || !validateSemver(newReleaseForm.version)}>
              {createReleaseMutation.isPending ? 'Creating...' : 'Create Release'}
            </Button>
          </form>
        </SheetContent>
      </Sheet>

      <Dialog open={Boolean(uploadTarget)} onOpenChange={(open) => !open && setUploadTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Firmware</DialogTitle>
            <DialogDescription>Upload a `.bin` firmware file for {uploadTarget?.version}</DialogDescription>
          </DialogHeader>

          <div
            className="rounded-[var(--radius-card)] border border-dashed p-6 text-center"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const file = event.dataTransfer.files?.[0];
              if (file && file.name.endsWith('.bin')) {
                setUploadFile(file);
              }
            }}
          >
            <p className="text-sm">Drag and drop .bin file</p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">or click to browse</p>
            <input
              type="file"
              accept=".bin"
              className="mt-3 block w-full text-xs"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setUploadFile(file);
                }
              }}
            />
            {uploadFile ? (
              <p className="mt-2 text-xs text-[var(--text-secondary)]">
                {uploadFile.name} ({(uploadFile.size / 1024).toFixed(2)} KB)
              </p>
            ) : null}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setUploadTarget(null)}>
              Cancel
            </Button>
            <Button
              disabled={!uploadFile || uploadFirmwareMutation.isPending || !uploadTarget}
              onClick={() => {
                if (!uploadTarget || !uploadFile) {
                  return;
                }
                uploadFirmwareMutation.mutate(
                  { releaseId: uploadTarget.id, file: uploadFile },
                  {
                    onSuccess: () => {
                      setUploadTarget(null);
                      setUploadFile(null);
                    },
                  },
                );
              }}
            >
              {uploadFirmwareMutation.isPending ? 'Uploading...' : 'Upload'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
