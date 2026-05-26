import { apiRequest } from '@/api/client';
import type { FirmwareCheckResponse } from '@/types';

export function manualFirmwareCheck(mac: string, version: string) {
  return apiRequest<FirmwareCheckResponse>(
    `/smart_switch/check?mac=${encodeURIComponent(mac)}&ver=${encodeURIComponent(version)}`,
    {
      auth: false,
    },
  );
}
