export interface Release {
  id: string;
  device_type: string;
  version: string;
  rollout_percentage: number;
  enabled: boolean;
  notes: string | null;
  firmware_file_id: string | null;
  sha256: string | null;
  size: number | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  device_type: string;
  mac: string;
  current_version: string;
  checked_at: string;
  result:
    | 'blocked'
    | 'invalid_version'
    | 'no_active_release'
    | 'version_not_greater'
    | 'rollout_not_included'
    | 'update_available'
    | 'override_invalid'
    | 'error_fallback';
  chosen_version: string | null;
  chosen_release_id: string | null;
  message: string | null;
  request_id: string | null;
  response: {
    update_available: boolean;
    version: string | null;
    firmware_url: string | null;
    sha256: string | null;
    size: number | null;
  };
}

export interface Override {
  id: string;
  device_type: string;
  mac: string;
  version: string;
  reason: string | null;
  updated_at: string;
}

export interface HealthResponse {
  status: 'ok' | string;
  now: string;
}

export interface FirmwareCheckResponse {
  update_available: boolean;
  version: string | null;
  firmware_url: string | null;
  sha256: string | null;
  size: number | null;
}
