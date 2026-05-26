import { apiRequest } from '@/api/client';
import type { Override } from '@/types';

export interface UpsertOverrideBody {
  version: string;
  reason: string | null;
}

export function getOverrides(deviceType: string) {
  return apiRequest<{ overrides: Override[] }>(`/admin/overrides/${encodeURIComponent(deviceType)}`);
}

export function upsertOverride(deviceType: string, mac: string, body: UpsertOverrideBody) {
  return apiRequest<Override>(`/admin/overrides/${encodeURIComponent(deviceType)}/${encodeURIComponent(mac)}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export function deleteOverride(deviceType: string, mac: string) {
  return apiRequest<{ message: string }>(`/admin/overrides/${encodeURIComponent(deviceType)}/${encodeURIComponent(mac)}`, {
    method: 'DELETE',
  });
}
