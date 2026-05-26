export const queryKeys = {
  health: ['health'] as const,
  releases: (deviceType: string) => ['releases', deviceType] as const,
  overrides: (deviceType: string) => ['overrides', deviceType] as const,
};
