import { formatDistanceToNowStrict } from 'date-fns';

export function formatRelativeTime(value: string): string {
  try {
    return `${formatDistanceToNowStrict(new Date(value), { addSuffix: true })}`;
  } catch {
    return value;
  }
}
