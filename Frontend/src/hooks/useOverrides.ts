import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteOverride, getOverrides, upsertOverride } from '@/api';
import { queryKeys } from '@/hooks/queryKeys';
import type { Override } from '@/types';

export function useOverrides(deviceType: string) {
  return useQuery({
    queryKey: queryKeys.overrides(deviceType),
    queryFn: async () => {
      const data = await getOverrides(deviceType);
      return data.overrides;
    },
    enabled: Boolean(deviceType),
  });
}

export function useUpsertOverride() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      deviceType,
      mac,
      version,
      reason,
    }: {
      deviceType: string;
      mac: string;
      version: string;
      reason: string | null;
    }) => upsertOverride(deviceType, mac, { version, reason }),
    onSuccess: (_result, { deviceType }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.overrides(deviceType) });
    },
  });
}

export function useDeleteOverride(deviceType: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ mac }: { mac: string }) => deleteOverride(deviceType, mac),
    onMutate: async ({ mac }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.overrides(deviceType) });
      const previous = queryClient.getQueryData<Override[]>(queryKeys.overrides(deviceType));
      if (previous) {
        queryClient.setQueryData<Override[]>(
          queryKeys.overrides(deviceType),
          previous.filter((entry) => entry.mac !== mac),
        );
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.overrides(deviceType), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.overrides(deviceType) });
    },
  });
}
