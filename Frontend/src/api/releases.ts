import { apiRequest } from '@/api/client';
import type { Release } from '@/types';

export interface CreateReleaseBody {
  device_type: string;
  version: string;
  rollout_percentage: number;
  enabled: boolean;
  notes: string | null;
}

export interface UploadFirmwareResponse {
  file_id: string;
  sha256: string;
  size: number;
  mime: string;
  filename: string;
}

export function getReleases(deviceType: string) {
  return apiRequest<{ releases: Release[] }>(`/admin/releases/${encodeURIComponent(deviceType)}`);
}

export function createRelease(body: CreateReleaseBody) {
  return apiRequest<Release>('/admin/releases', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function uploadReleaseFirmware(releaseId: string, file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest<UploadFirmwareResponse>(`/admin/releases/${releaseId}/firmware`, {
    method: 'POST',
    body: formData,
  });
}

export function setReleaseEnabled(releaseId: string, enabled: boolean) {
  return apiRequest<Release>(`/admin/releases/${releaseId}/enabled`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  });
}

export function setReleaseRollout(releaseId: string, rollout_percentage: number) {
  return apiRequest<Release>(`/admin/releases/${releaseId}/rollout`, {
    method: 'PATCH',
    body: JSON.stringify({ rollout_percentage }),
  });
}
