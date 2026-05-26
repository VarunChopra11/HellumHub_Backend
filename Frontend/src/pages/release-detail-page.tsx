import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { useMutation } from '@tanstack/react-query';
import { Copy, Upload } from 'lucide-react';
import { useParams, useSearchParams } from 'react-router-dom';
import { manualFirmwareCheck } from '@/api';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
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
  Slider,
  Switch,
} from '@/components/ui';
import { useReleases, useToggleReleaseEnabled, useUpdateReleaseRollout, useUploadReleaseFirmware } from '@/hooks/useReleases';
import { formatBytes } from '@/lib/formatBytes';
import { validateMac } from '@/lib/validateMac';
import { validateSemver } from '@/lib/validateSemver';

function formatTimestamp(value: string): string {
  try {
    return format(new Date(value), 'MMM d, yyyy \'at\' hh:mm a');
  } catch {
    return value;
  }
}

function shortenSha(value: string | null): string {
  if (!value) {
    return 'N/A';
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}...${value.slice(-8)}`;
}

export function ReleaseDetailPage() {
  const { releaseId } = useParams();
  const [searchParams] = useSearchParams();
  const deviceType = searchParams.get('device_type') || 'smart_switch';

  const releasesQuery = useReleases(deviceType);
  const toggleEnabledMutation = useToggleReleaseEnabled(deviceType);
  const updateRolloutMutation = useUpdateReleaseRollout(deviceType);
  const uploadFirmwareMutation = useUploadReleaseFirmware(deviceType);

  const release = useMemo(() => releasesQuery.data?.find((entry) => entry.id === releaseId), [releaseId, releasesQuery.data]);

  const [rolloutValue, setRolloutValue] = useState<number>(release?.rollout_percentage ?? 0);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [mac, setMac] = useState('AA:BB:CC:DD:EE:FF');
  const [version, setVersion] = useState('1.0.0');
  const [responseTime, setResponseTime] = useState<number | null>(null);

  const checkMutation = useMutation({
    mutationFn: async ({ macAddress, currentVersion }: { macAddress: string; currentVersion: string }) => {
      const start = performance.now();
      const response = await manualFirmwareCheck(macAddress, currentVersion);
      setResponseTime(Math.round(performance.now() - start));
      return response;
    },
  });

  if (releasesQuery.isLoading) {
    return <p className="text-sm text-[var(--text-secondary)]">Loading release...</p>;
  }

  if (!release) {
    return (
      <Card>
        <CardContent className="py-10">
          <p className="text-sm text-[var(--text-secondary)]">
            Release not found. Open this page from Releases so device type context is attached.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-sm text-[var(--text-secondary)]">Releases &gt; {release.version}</div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Release Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 text-sm">
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">ID</span>
                <span className="font-mono text-xs">{release.id}</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Device Type</span>
                <span>{release.device_type}</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Version</span>
                <Badge variant={release.enabled ? 'success' : 'default'}>{release.version}</Badge>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Rollout %</span>
                <span>{release.rollout_percentage}%</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Firmware</span>
                <span>{release.firmware_file_id ? 'Uploaded' : 'Missing'}</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center gap-2">
                <span className="text-[var(--text-secondary)]">SHA256</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs">{shortenSha(release.sha256)}</span>
                  {release.sha256 ? (
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => {
                        void navigator.clipboard.writeText(release.sha256 as string);
                      }}
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  ) : null}
                </div>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Size</span>
                <span>{formatBytes(release.size)}</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Created</span>
                <span>{formatTimestamp(release.created_at)}</span>
              </div>
              <div className="grid grid-cols-[180px_1fr] items-center">
                <span className="text-[var(--text-secondary)]">Updated</span>
                <span>{formatTimestamp(release.updated_at)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
              <CardDescription>Edit release status and rollout.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="detail-enabled">Enabled</Label>
                <Switch
                  id="detail-enabled"
                  checked={release.enabled}
                  onCheckedChange={(enabled) => toggleEnabledMutation.mutate({ releaseId: release.id, enabled })}
                />
              </div>
              <div className="space-y-2">
                <Label>Rollout</Label>
                <Slider value={[rolloutValue]} min={0} max={100} step={1} onValueChange={(value) => setRolloutValue(value[0] ?? 0)} />
                <p className="text-xs text-[var(--text-secondary)]">{rolloutValue}%</p>
                <Button
                  variant="secondary"
                  className="w-full"
                  disabled={updateRolloutMutation.isPending}
                  onClick={() => updateRolloutMutation.mutate({ releaseId: release.id, rolloutPercentage: rolloutValue })}
                >
                  Save Rollout
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Danger Zone</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {release.enabled ? (
                <Button
                  variant="destructive"
                  className="w-full"
                  onClick={() => toggleEnabledMutation.mutate({ releaseId: release.id, enabled: false })}
                >
                  Disable Release
                </Button>
              ) : null}
              <Button variant="secondary" className="w-full" onClick={() => setUploadOpen(true)}>
                <Upload className="h-4 w-4" />
                Upload New Firmware
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Manual OTA Test</CardTitle>
          <CardDescription>Checks `GET /smart_switch/check` with the provided parameters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="test-mac">MAC Address</Label>
              <Input id="test-mac" value={mac} onChange={(event) => setMac(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="test-version">Current Version</Label>
              <Input id="test-version" value={version} onChange={(event) => setVersion(event.target.value)} />
            </div>
            <div className="flex items-end">
              <Button
                className="w-full"
                disabled={checkMutation.isPending || !validateMac(mac) || !validateSemver(version)}
                onClick={() => checkMutation.mutate({ macAddress: mac, currentVersion: version })}
              >
                {checkMutation.isPending ? 'Checking...' : 'Run Check'}
              </Button>
            </div>
          </div>
          {responseTime !== null ? <p className="text-xs text-[var(--text-secondary)]">Response time: {responseTime} ms</p> : null}
          <pre className="overflow-x-auto rounded-[var(--radius-card)] border bg-black/40 p-4 text-xs leading-5 text-[#d4d4d4]">
            <code>{JSON.stringify(checkMutation.data ?? { message: 'Run a test to see response JSON' }, null, 2)}</code>
          </pre>
        </CardContent>
      </Card>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Firmware</DialogTitle>
            <DialogDescription>Upload a `.bin` file for {release.version}</DialogDescription>
          </DialogHeader>
          <Input
            type="file"
            accept=".bin"
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              setUploadFile(selected);
            }}
          />
          <DialogFooter>
            <Button variant="secondary" onClick={() => setUploadOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!uploadFile || uploadFirmwareMutation.isPending}
              onClick={() => {
                if (!uploadFile) {
                  return;
                }
                uploadFirmwareMutation.mutate(
                  { releaseId: release.id, file: uploadFile },
                  {
                    onSuccess: () => {
                      setUploadOpen(false);
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
