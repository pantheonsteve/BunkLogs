import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../api';

/**
 * Step 7_3 — React hook wrapping the Supervision admin endpoints.
 *
 * Returns the Supervision rows where the current user has visibility (admin
 * for full lists; supervisors for their own row scope via the
 * supervisor_membership_id filter). Mutations are not exposed here; the
 * Admin Assignments surface (Step 7_13) wires Create/Patch separately.
 *
 * @param {{
 *   supervisorMembershipId?: number|string,
 *   targetType?: 'membership'|'role_in_program'|'bunk',
 *   isActive?: boolean,
 *   autoLoad?: boolean,
 * }} options
 *   `supervisorMembershipId` scopes the list to one supervisor (the common
 *   case). `autoLoad` defaults to true; set false when callers want to load
 *   on demand via the returned `refetch`.
 *
 * @returns {{
 *   supervisions: object[],
 *   isLoading: boolean,
 *   error: Error|null,
 *   refetch: () => Promise<void>,
 * }}
 */
export const SUPERVISION_TARGET_TYPES = Object.freeze({
  MEMBERSHIP: 'membership',
  ROLE_IN_PROGRAM: 'role_in_program',
  BUNK: 'bunk',
});

export const SUPERVISIONS_PATH = '/api/v1/supervisions/';

function buildParams({ supervisorMembershipId, targetType, isActive }) {
  const params = {};
  if (supervisorMembershipId !== undefined && supervisorMembershipId !== null && supervisorMembershipId !== '') {
    params.supervisor_membership_id = supervisorMembershipId;
  }
  if (targetType) {
    params.target_type = targetType;
  }
  if (typeof isActive === 'boolean') {
    params.is_active = isActive ? 'true' : 'false';
  }
  return params;
}

function extractList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export default function useSupervision({
  supervisorMembershipId,
  targetType,
  isActive,
  autoLoad = true,
} = {}) {
  const [supervisions, setSupervisions] = useState([]);
  const [isLoading, setIsLoading] = useState(autoLoad);
  const [error, setError] = useState(null);

  const params = useMemo(
    () => buildParams({ supervisorMembershipId, targetType, isActive }),
    [supervisorMembershipId, targetType, isActive],
  );

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.get(SUPERVISIONS_PATH, { params });
      setSupervisions(extractList(resp?.data));
    } catch (err) {
      setError(err);
      setSupervisions([]);
    } finally {
      setIsLoading(false);
    }
  }, [params]);

  useEffect(() => {
    if (!autoLoad) return;
    refetch();
  }, [autoLoad, refetch]);

  return { supervisions, isLoading, error, refetch };
}
