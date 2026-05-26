export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Session expired';
    }
    if (error.status === 409) {
      return error.detail || 'Version already exists';
    }
    if (error.status === 422) {
      return error.detail || 'Validation failed';
    }
    if (error.status >= 500) {
      return 'Server error, please try again';
    }
    return error.detail || error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unexpected error';
}
