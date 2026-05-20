import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../api';

/**
 * Step 7_4 — React hook wrapping the Admin-only audit endpoints.
 *
 * Three modes, picked by which props you pass:
 *
 * 1. By content (`contentType` + `contentId`) — chronological trail for a
 *    specific content row. Writes an `AUDIT_VIEW` meta-event on the server.
 * 2. By actor (`membershipId`) — newest-first events authored by a given
 *    Membership.
 * 3. Admin overrides (`mode: 'admin-overrides'`, optional `since` ISO date) —
 *    org-wide override list, defaults to last 30 days.
 *
 * Returns `{ events, isLoading, error, refetch }`. The hook does not gate
 * on role; callers should render <AuditTrail> only for Admins.
 *
 * @param {{
 *   contentType?: string,
 *   contentId?: string|number,
 *   membershipId?: number|string,
 *   mode?: 'by-content'|'by-actor'|'admin-overrides',
 *   since?: string,
 *   autoLoad?: boolean,
 * }} options
 */
export const AUDIT_BASE_PATH = '/api/v1/audit/';

function resolveRequest({
  contentType,
  contentId,
  membershipId,
  mode,
  since,
}) {
  if (mode === 'by-actor') {
    return {
      url: `${AUDIT_BASE_PATH}by-actor/`,
      params: { membership_id: membershipId },
      ready: Boolean(membershipId),
    };
  }
  if (mode === 'admin-overrides') {
    const params = {};
    if (since) params.since = since;
    return { url: `${AUDIT_BASE_PATH}admin-overrides/`, params, ready: true };
  }
  return {
    url: AUDIT_BASE_PATH,
    params: { content_type: contentType, content_id: contentId },
    ready: Boolean(contentType) && contentId !== undefined && contentId !== null && contentId !== '',
  };
}

function extractList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export default function useAuditTrail({
  contentType,
  contentId,
  membershipId,
  mode = 'by-content',
  since,
  autoLoad = true,
} = {}) {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useMemo(
    () => resolveRequest({ contentType, contentId, membershipId, mode, since }),
    [contentType, contentId, membershipId, mode, since],
  );

  const refetch = useCallback(async () => {
    if (!request.ready) {
      setEvents([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.get(request.url, { params: request.params });
      setEvents(extractList(resp?.data));
    } catch (err) {
      setError(err);
      setEvents([]);
    } finally {
      setIsLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (!autoLoad) return;
    refetch();
  }, [autoLoad, refetch]);

  return { events, isLoading, error, refetch };
}
