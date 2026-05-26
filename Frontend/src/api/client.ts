import { ApiError } from '@/lib/apiError';

const KEY_STORAGE = 'ota_admin_key';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler;
}

export function getApiKey(): string | null {
  return localStorage.getItem(KEY_STORAGE);
}

export function setApiKey(value: string) {
  localStorage.setItem(KEY_STORAGE, value);
}

export function clearApiKey() {
  localStorage.removeItem(KEY_STORAGE);
}

interface RequestOptions extends RequestInit {
  auth?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const requestHeaders = new Headers(headers);

  if (!requestHeaders.has('Content-Type') && !(rest.body instanceof FormData) && rest.method && rest.method !== 'GET') {
    requestHeaders.set('Content-Type', 'application/json');
  }

  if (auth) {
    const key = getApiKey();
    if (!key) {
      throw new ApiError(401, 'Missing API key');
    }
    requestHeaders.set('x-api-key', key);
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: requestHeaders,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach server');
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null
        ? (payload.detail as string | undefined) || (payload.message as string | undefined)
        : undefined;

    if (response.status === 401) {
      clearApiKey();
      unauthorizedHandler?.();
    }

    throw new ApiError(response.status, detail || response.statusText, detail);
  }

  return payload as T;
}
