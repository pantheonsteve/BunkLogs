/**
 * Unified Group Dashboard page at `/dashboards/group/:groupId`.
 *
 * Replaces the per-role `/unit-head/bunks/:id` and
 * `/camper-care/bunks/:id` wrappers AND generalizes to non-bunk
 * groups (unit, division, classroom). Backend resolves the caller's
 * role server-side and dispatches on `group.group_type` to return
 * the right payload shape; this page reads `role_context.group_type`
 * to pick the right presentational component.
 *
 * URL contract: date is in the query string (`?date=YYYY-MM-DD`) so
 * deep links to past days are shareable. Auto-refreshes today's view
 * every 60s; past dates are static.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import BunkDashboard, { BunkDashboardOrdersAndNotes } from '../../components/BunkDashboard';
import ClassroomDashboard from '../../components/ClassroomDashboard';
import DivisionDashboard from '../../components/DivisionDashboard';
import UnitDashboard from '../../components/UnitDashboard';
import UnsupportedGroupDashboard from '../../components/UnsupportedGroupDashboard';
import GroupTemplateResponses from '../../components/GroupTemplateResponses';
import { fetchGroupDashboard } from '../../api/dashboards';

const REFRESH_INTERVAL_MS = 60_000;

const FALLBACK_BACK_TO = '/dashboards';

const BACK_TO_BY_ROLE = Object.freeze({
  counselor: '/counselor',
  camper_care: '/camper-care',
  unit_head: '/unit-head',
  leadership_team: '/leadership-team',
  classroom_author: '/dashboards',
});

const ADMIN_BACK_TO = '/groups/performance';

function backToFor(role, { date, program, tab } = {}) {
  if (role === 'admin') {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (program) params.set('program', program);
    if (tab === 'past') params.set('tab', 'past');
    const query = params.toString();
    return query ? `${ADMIN_BACK_TO}?${query}` : ADMIN_BACK_TO;
  }
  return BACK_TO_BY_ROLE[role] ?? FALLBACK_BACK_TO;
}

// Wrap the legacy BunkDashboard so the dispatch test can target it
// with the same `data-testid="group-dashboard-{type}"` pattern as
// the new components.
function BunkDashboardWrapped(props) {
  return (
    <div data-testid="group-dashboard-bunk">
      <BunkDashboard {...props} />
    </div>
  );
}

const COMPONENT_BY_GROUP_TYPE = Object.freeze({
  bunk: BunkDashboardWrapped,
  unit: UnitDashboard,
  division: DivisionDashboard,
  classroom: ClassroomDashboard,
});

export default function GroupDashboardPage() {
  const { groupId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [errorStatus, setErrorStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await fetchGroupDashboard(groupId, {
        date: dateParam || undefined,
      });
      setData(payload);
      setError('');
      setErrorStatus(null);
    } catch (err) {
      const status = err?.response?.status ?? null;
      const detail = err?.response?.data?.detail;
      const body = err?.response?.data;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(body) && typeof body[0] === 'string'
            ? body[0]
            : typeof body === 'string'
              ? body
              : err?.message || 'Could not load this dashboard.';
      setError(message);
      setErrorStatus(status);
    } finally {
      setLoading(false);
    }
  }, [groupId, dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  const isToday = useMemo(() => {
    if (!data?.header?.date || !data?.header?.today) return false;
    return data.header.date === data.header.today;
  }, [data]);

  useEffect(() => {
    if (!isToday) return undefined;
    const id = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isToday, load]);

  const handleDateChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next) params.set('date', next);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading group dashboard…</p>
      </div>
    );
  }

  // 400 from the backend means the group_type isn't supported yet —
  // surface the friendlier empty-state instead of a generic error.
  if (error && !data) {
    if (errorStatus === 400) {
      return (
        <UnsupportedGroupDashboard
          message={error}
          backTo={FALLBACK_BACK_TO}
        />
      );
    }
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="group-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const role = data?.role_context?.role;
  const groupType = data?.role_context?.group_type;
  const Dash = COMPONENT_BY_GROUP_TYPE[groupType];
  const backTo = backToFor(role, {
    date: dateParam || data?.header?.date,
    program: searchParams.get('program') || '',
    tab: searchParams.get('tab') || '',
  });

  if (!Dash) {
    return (
      <UnsupportedGroupDashboard
        groupType={groupType}
        backTo={backTo}
      />
    );
  }

  const profileLinkContext = {
    groupId,
    date: dateParam || data?.header?.date || undefined,
  };

  const sharedProps = {
    data,
    selectedDate: dateParam || data?.header?.date,
    onDateChange: handleDateChange,
    backTo,
    programName: data?.header?.program_name,
    profileLinkContext,
  };

  const templatesSection = (
    <div className="px-4 sm:px-6 lg:px-8 w-full max-w-[80rem] mx-auto">
      <GroupTemplateResponses
        templates={data?.templates}
        profileLinkContext={profileLinkContext}
        groupLabel={
          data?.header?.bunk?.name
          || data?.header?.group?.name
          || null
        }
        onNoteCreated={load}
      />
    </div>
  );

  if (groupType === 'bunk') {
    return (
      <>
        <Dash
          {...sharedProps}
          showScoreGrid={false}
          showOrders={false}
          showNotes={false}
        />
        {templatesSection}
        <div className="px-4 sm:px-6 lg:px-8 pb-8 w-full max-w-[80rem] mx-auto space-y-5">
          <BunkDashboardOrdersAndNotes
            data={data}
            profileLinkContext={profileLinkContext}
          />
        </div>
      </>
    );
  }

  return (
    <>
      <Dash {...sharedProps} />
      {templatesSection}
    </>
  );
}
