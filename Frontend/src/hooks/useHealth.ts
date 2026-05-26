import { useQuery } from '@tanstack/react-query';
import { getHealth } from '@/api';
import { queryKeys } from '@/hooks/queryKeys';

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: getHealth,
    refetchInterval: 30000,
    retry: 1,
  });
}
