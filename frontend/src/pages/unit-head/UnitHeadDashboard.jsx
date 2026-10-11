/**
 * Unit Head home (2027 refresh, 8_5).
 *
 * Header with day stepper + my-reflection state, three attention cards,
 * a bunk card grid, the selected bunk's camper scores, and staff
 * reflections. Bunk list and my-reflection state come from the UH
 * dashboard (today only, polled); everything date-dependent comes from
 * each supervised bunk's existing group dashboard payload plus the staff
 * reflections endpoint, fetched for the selected date.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Hand, HeartHandshake, LogOut } from 'lucide-react';
import AttentionCard from '../../components/ui/AttentionCard';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import DayStepper from '../../components/ui/DayStepper';
import EmptyState from '../../components/ui/EmptyState';
import InitialsAvatar from '../../components/ui/InitialsAvatar';
import RatingCell from '../../components/ui/RatingCell';
import CamperScoresTable from '../../components/supervisor/CamperScoresTable';
import GroupCard from '../../components/supervisor/GroupCard';
import SupervisorHeading from '../../components/supervisor/SupervisorHeading';
import { bunkStats, camperShortName } from '../../components/supervisor/bunkStats';
import { fetchGroupDashboard } from '../../api/dashboards';
import { fetchUnitHeadDashboard, fetchUnitHeadStaffReflections } from '../../api/unitHead';
import { useTerm } from '../../context/OrgBrandingContext';
import { groupDashboardLink, profileLink, withDateParam } from '../../utils/dashboardLinks';

const REFRESH_INTERVAL_MS = 60_000;

const SELF_STATE = {
  complete: { label: 'submitted', tone: 'ok' },
  day_off: { label: 'day off', tone: 'neutral' },
  missing: { label: 'not yet', tone: 'warn' },
};

function titleCase(s) {
  return String(s || '').replace(/\b\w/g, (c) => c.toUpperCase());
}

function countNoun(term, key, n) {
  return `${n} ${term(key, { plural: n !== 1 })}`;
}

function supportNeeded(answers) {
  const v = answers?.staff_care_support_needed;
  return v === true || v === 'yes';
}

function StaffRow({ entry, to }) {
  const day = entry.answers?.overall_day;
  let score;
  if (entry.state === 'complete' && typeof day === 'number') {
    score = <RatingCell value={day} size="sm" label={`${entry.counselor_name} day`} />;
  } else {
    score = (
      <span className="inline-flex items-center h-6 px-1.5 rounded-[5px] bg-line-soft text-xs font-bold text-ink-2">
        {entry.state === 'day_off' ? 'Day off' : '—'}
      </span>
    );
  }
  return (
    <Link
      to={to}
      data-testid={`uh-staff-${entry.person_id}`}
      className="flex items-center gap-2.5 min-h-[52px] border-t border-line-soft text-ink hover:bg-line-soft/60"
    >
      <InitialsAvatar name={entry.counselor_name} size="sm" aria-hidden="true" />
      <span className="flex-1 min-w-0">
        <span className="block text-[13px] font-semibold truncate">{entry.counselor_name}</span>
        <span className="block text-xs text-muted">{entry.group}</span>
      </span>
      {supportNeeded(entry.answers) && <Badge tone="danger" className="font-bold">Support</Badge>}
      {score}
    </Link>
  );
}

export default function UnitHeadDashboard() {
  const term = useTerm();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlDate = searchParams.get('date') || '';

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [bunkData, setBunkData] = useState({});
  const [bunksLoading, setBunksLoading] = useState(false);
  const [staff, setStaff] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const detailRef = useRef(null);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    if (silent) setRefreshing(true);
    try {
      const next = await fetchUnitHeadDashboard({ noCache: silent });
      setData(next);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const id = setInterval(() => load({ silent: true }), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  const today = data?.today;
  const selectedDate = urlDate || today;
  const bunks = useMemo(() => data?.bunks || [], [data]);
  const bunkIdsKey = bunks.map((b) => b.id).join(',');

  useEffect(() => {
    if (!selectedDate || !bunkIdsKey) return undefined;
    let active = true;
    const ids = bunkIdsKey.split(',');
    setBunksLoading(true);
    Promise.allSettled(ids.map((id) => fetchGroupDashboard(id, { date: selectedDate })))
      .then((results) => {
        if (!active) return;
        const next = {};
        results.forEach((r, i) => {
          if (r.status === 'fulfilled' && r.value) next[ids[i]] = r.value;
        });
        setBunkData(next);
        setBunksLoading(false);
      });
    return () => { active = false; };
  }, [bunkIdsKey, selectedDate]);

  useEffect(() => {
    if (!selectedDate) return undefined;
    let active = true;
    fetchUnitHeadStaffReflections({ date: selectedDate })
      .then((payload) => { if (active) setStaff(payload); })
      .catch(() => { if (active) setStaff(null); });
    return () => { active = false; };
  }, [selectedDate]);

  const handleDateChange = (iso) => {
    const next = new URLSearchParams(searchParams);
    if (!iso || iso === today) next.delete('date');
    else next.set('date', iso);
    setSearchParams(next, { replace: true });
  };

  const cards = useMemo(() => bunks.map((bunk) => {
    const payload = bunkData[String(bunk.id)];
    const stats = payload ? bunkStats(payload) : null;
    return {
      bunk,
      payload,
      stats,
      done: stats ? stats.done : (bunk.completion?.submitted ?? 0),
      total: stats ? stats.total : (bunk.completion?.expected ?? 0),
      camperCount: stats
        ? stats.camperCount
        : (bunk.completion?.expected ?? 0) + (bunk.completion?.off_camp ?? 0),
    };
  }), [bunks, bunkData]);

  const toProfile = useCallback(
    (bunkId) => (id) => profileLink(id, { groupId: bunkId, date: selectedDate }),
    [selectedDate],
  );

  const attention = useMemo(() => {
    const lists = { uh: [], cc: [], off: [] };
    cards.forEach(({ bunk, payload }) => {
      if (!payload) return;
      const link = toProfile(bunk.id);
      const row = (c) => ({
        id: `${bunk.id}-${c.id}`,
        name: camperShortName(c),
        where: bunk.name,
        to: link(c.id),
      });
      lists.uh.push(...(payload.help_requested || []).map(row));
      lists.cc.push(...(payload.camper_care_help_requested || []).map(row));
      lists.off.push(...(payload.off_camp || []).map(row));
    });
    return lists;
  }, [cards, toProfile]);

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1240px] mx-auto">
        <p className="text-muted">Loading dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1240px] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-warn-soft bg-warn-soft px-4 py-3 text-sm text-warn-ink"
        >
          {error}
        </div>
      </div>
    );
  }

  const roleTitle = titleCase(term('unit_head'));
  const unitNames = [...new Set(bunks.map((b) => b.unit_name).filter(Boolean))];
  const pageTitle = unitNames.length ? unitNames.join(' · ') : titleCase(term('unit'));
  const counselorCount = new Set(bunks.flatMap((b) => b.counselor_names || [])).size;
  const camperTotal = cards.reduce((n, c) => n + c.camperCount, 0);
  const logsDone = cards.reduce((n, c) => n + c.done, 0);
  const logsTotal = cards.reduce((n, c) => n + c.total, 0);
  const summary = [
    countNoun(term, 'bunk', bunks.length),
    countNoun(term, 'camper', camperTotal),
    countNoun(term, 'counselor', counselorCount),
  ].join(' · ');

  const selfState = data?.self_reflection?.state ?? 'missing';
  const self = SELF_STATE[selfState] || SELF_STATE.missing;
  const isToday = !urlDate || urlDate === today;

  const selected = cards.find((c) => c.bunk.id === selectedId) || cards[0];
  const categories = cards.find((c) => c.stats?.averages.length)?.stats.averages.map((a) => a.label) || [];

  const staffEntries = (staff?.bunks || []).flatMap((b) => (
    (b.counselor_self_reflections || []).map((e) => ({ ...e, group: b.name }))
  ));
  const staffCounts = staffEntries.reduce((acc, e) => {
    acc[e.state] = (acc[e.state] || 0) + 1;
    return acc;
  }, {});
  const staffLink = withDateParam('/unit-head/staff-reflections', urlDate);

  const selectBunk = (id) => {
    setSelectedId(id);
    detailRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div data-testid="uh-dashboard" className="w-full">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 px-4 sm:px-6 lg:px-8 py-3.5 bg-white dark:bg-gray-900 border-b border-line">
        <DayStepper
          selectedIso={selectedDate}
          todayIso={today}
          onChange={handleDateChange}
          refreshing={refreshing}
          testIdPrefix="uh"
          className="w-full sm:w-auto sm:min-w-[320px]"
        />
        <div className="flex flex-wrap items-center gap-3 sm:ml-auto" data-testid="uh-self-reflection" data-state={selfState}>
          <Badge tone={self.tone} dot size="md" className="font-semibold" data-testid="uh-self-reflection-state">
            Your reflection: {self.label}
          </Badge>
          <Button as={Link} to="/unit-head/self-reflection" data-testid="uh-self-reflection-action">
            {selfState === 'missing' ? 'Write reflection' : 'Edit reflection'}
          </Button>
          <Link
            to="/unit-head/self-reflection/history"
            className="text-[13px] font-semibold text-brand hover:text-brand-hover"
          >
            History
          </Link>
        </div>
      </div>

      <main className="px-4 sm:px-6 lg:px-8 pt-7 pb-12 flex flex-col gap-6 max-w-[1240px] w-full">
        <SupervisorHeading
          eyebrow={roleTitle}
          title={pageTitle}
          summary={summary}
          progressLabel={isToday ? 'Logs today' : 'Logs'}
          done={logsDone}
          total={logsTotal}
          progressTestId="uh-logs-progress"
        />

        {bunks.length === 0 ? (
          <EmptyState title={`No ${term('bunk', { plural: true })} assigned`}>
            {`You aren't supervising any ${term('bunk', { plural: true })} in the current program.`}
          </EmptyState>
        ) : (
          <>
            <div className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
              <AttentionCard
                title={`${roleTitle} help requested`}
                icon={Hand}
                tone="warn"
                rows={attention.uh}
                maxRows={5}
                data-testid="uh-attention-uh-help"
              />
              <AttentionCard
                title={`${term('camper_care')} help requested`}
                icon={HeartHandshake}
                tone="danger"
                rows={attention.cc}
                maxRows={5}
                data-testid="uh-attention-cc-help"
              />
              <AttentionCard
                title="Not on camp"
                icon={LogOut}
                tone="neutral"
                rows={attention.off}
                maxRows={5}
                data-testid="uh-attention-off-camp"
              />
            </div>

            <section aria-labelledby="uh-groups" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 id="uh-groups" className="text-base font-bold text-ink">
                  My {term('bunk', { plural: true })}
                </h2>
                {categories.length > 0 && (
                  <span className="text-[13px] text-muted">
                    Avg {isToday ? 'today' : 'this day'} · {categories.join(' · ')}
                  </span>
                )}
              </div>
              <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
                {cards.map(({ bunk, stats, done, total }) => (
                  <GroupCard
                    key={bunk.id}
                    testId={`uh-bunk-card-${bunk.id}`}
                    name={bunk.name}
                    staff={(bunk.counselor_names || []).join(', ')}
                    done={done}
                    total={total}
                    averages={stats?.averages}
                    flags={stats?.flags || 0}
                    selected={selected?.bunk.id === bunk.id}
                    onSelect={() => selectBunk(bunk.id)}
                  />
                ))}
              </div>
            </section>

            {selected && (
              <Card
                as="section"
                ref={detailRef}
                aria-labelledby="uh-detail"
                className="px-[22px] py-5 flex flex-col gap-3.5 scroll-mt-4"
                data-testid="uh-detail"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <h2 id="uh-detail" className="text-base font-bold text-ink">
                      {selected.bunk.name} · {titleCase(term('camper'))} daily scores
                    </h2>
                    <p className="text-[13px] text-muted mt-0.5">
                      {[
                        selected.bunk.counselor_names?.length
                          ? `${titleCase(term('counselor', { plural: selected.bunk.counselor_names.length !== 1 }))} ${selected.bunk.counselor_names.join(' and ')}`
                          : null,
                        `${selected.done} of ${selected.total} logged`,
                      ].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <Button
                    as={Link}
                    variant="secondary"
                    size="sm"
                    className="min-h-9 text-[13px]"
                    to={groupDashboardLink(selected.bunk.id, { date: urlDate || undefined })}
                    data-testid="uh-detail-open"
                  >
                    Open full dashboard
                  </Button>
                </div>
                {selected.payload ? (
                  <CamperScoresTable
                    payload={selected.payload}
                    camperLabel={titleCase(term('camper'))}
                    linkFor={toProfile(selected.bunk.id)}
                    uhLabel={`${roleTitle} help`}
                  />
                ) : (
                  <p className="text-sm text-muted">
                    {bunksLoading ? 'Loading…' : 'Could not load this bunk.'}
                  </p>
                )}
              </Card>
            )}

            <Card as="section" aria-labelledby="uh-staff" className="px-[22px] py-5 flex flex-col gap-2.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 id="uh-staff" className="text-base font-bold text-ink">
                  <Link to={staffLink} className="hover:underline">
                    {titleCase(term('counselor'))} reflections {isToday ? 'today' : 'this day'}
                  </Link>
                </h2>
                {staffEntries.length > 0 && (
                  <span className="text-[13px] text-ink-2" data-testid="uh-staff-summary">
                    {staffCounts.complete || 0} submitted · {staffCounts.day_off || 0} day off ·{' '}
                    {staffCounts.missing || 0} not yet
                  </span>
                )}
              </div>
              {staffEntries.length === 0 ? (
                <p className="text-[13px] text-muted">No staff reflections for this day.</p>
              ) : (
                <div className="grid gap-x-6 grid-cols-[repeat(auto-fill,minmax(250px,1fr))]">
                  {staffEntries.map((entry) => (
                    <StaffRow key={`${entry.group}-${entry.person_id}`} entry={entry} to={staffLink} />
                  ))}
                </div>
              )}
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
