const MAC_REGEX = /^[A-F0-9]{12}$/;

export function normalizeMac(input: string): string | null {
  const raw = input.replace(/[^a-fA-F0-9]/g, '').toUpperCase();
  if (!MAC_REGEX.test(raw)) {
    return null;
  }

  return raw.match(/.{1,2}/g)?.join(':') ?? null;
}

export function validateMac(input: string): boolean {
  return normalizeMac(input) !== null;
}
