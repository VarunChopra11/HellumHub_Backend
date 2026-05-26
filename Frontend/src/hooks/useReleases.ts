import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { compare } from 'semver';
import { createRelease, getReleases, setReleaseEnabled, setReleaseRollout, uploadReleaseFirmware } from '@/api';
import { queryKeys } from '@/hooks/queryKeys';
import type { Release } from '@/types';

export function useReleases(deviceType: string) {
  return useQuery({
    queryKey: queryKeys.releases(deviceType),
    queryFn: async () => {
      const data = await getReleases(deviceType);
      return data.releases.slice().sort((a, b) => {
        try {
          return compare(b.version, a.version);
        } catch {
          return b.version.localeCompare(a.version);
        }
      });
    },
    enabled: Boolean(deviceType),
  });
}

export function useCreateRelease(deviceType: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createRelease,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.releases(deviceType) });
    },
  });
}

export function useToggleReleaseEnabled(deviceType: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ releaseId, enabled }: { releaseId: string; enabled: boolean }) => setReleaseEnabled(releaseId, enabled),
    onMutate: async ({ releaseId, enabled }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.releases(deviceType) });
      const previous = queryClient.getQueryData<Release[]>(queryKeys.releases(deviceType));
      if (previous) {
        queryClient.setQueryData<Release[]>(
          queryKeys.releases(deviceType),
          previous.map((release) => (release.id === releaseId ? { ...release, enabled } : release)),
        );
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.releases(deviceType), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.releases(deviceType) });
    },
  });
}

export function useUpdateReleaseRollout(deviceType: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ releaseId, rolloutPercentage }: { releaseId: string; rolloutPercentage: number }) =>
      setReleaseRollout(releaseId, rolloutPercentage),
    onMutate: async ({ releaseId, rolloutPercentage }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.releases(deviceType) });
      const previous = queryClient.getQueryData<Release[]>(queryKeys.releases(deviceType));
      if (previous) {
        queryClient.setQueryData<Release[]>(
          queryKeys.releases(deviceType),
          previous.map((release) =>
            release.id === releaseId ? { ...release, rollout_percentage: rolloutPercentage } : release,
          ),
        );
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.releases(deviceType), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.releases(deviceType) });
    },
  });
}

export function useUploadReleaseFirmware(deviceType: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ releaseId, file }: { releaseId: string; file: File }) => uploadReleaseFirmware(releaseId, file),
    onSuccess: (_data, { releaseId, file }) => {
      queryClient.setQueryData<Release[]>(queryKeys.releases(deviceType), (current) =>
        current?.map((release) =>
          release.id === releaseId
            ? {
                ...release,
                firmware_file_id: 'pending',
                size: file.size,
              }
            : release,
        ),
      );
      queryClient.invalidateQueries({ queryKey: queryKeys.releases(deviceType) });
    },
  });
}
