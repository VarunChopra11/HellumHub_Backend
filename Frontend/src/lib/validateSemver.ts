import { valid } from 'semver';

export function validateSemver(version: string): boolean {
  return Boolean(valid(version.trim()));
}
