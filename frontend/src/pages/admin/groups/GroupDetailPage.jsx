/**
 * One group, as four tabs.
 *
 * Members / Staff / Supervision / Settings replaced a single scrolling
 * page that mixed the roster with CSV import and a "Deactivate" link two
 * inches from "rename". The Staff tab is labelled from the group's type,
 * so a classroom's authors read as Faculty and a team's as Staff without
 * either page knowing about the other tenant.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { BarChart3 } from 'lucide-react';

import api from '../../../api';
import { getAdminAssignmentFacets } from '../../../api/admin';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import PageHeader from '../../../components/ui/PageHeader';
import Toast, { useToast } from '../../../components/ui/Toast';
import { useTerm } from '../../../context/OrgBrandingContext';
import GroupRosterTab from './GroupRosterTab';
import GroupSettingsTab from './GroupSettingsTab';
import GroupSupervisionTab from './GroupSupervisionTab';
import { SUPERVISABLE_TYPES, authorTermKey, groupTypeLabel } from './groupTypes';

/**
 * Whether this org uses supervision at all.
 *
 * A religious school has no camper-care caseloads, so the tab would only
 * ever render an empty table. This is the surviving half of the old
 * `visibleSubTabs` facet check.
 */
function orgUsesSupervision(facets) {
  if (!facets) return true;
  return (facets.roles || []).includes('camper_care');
}

export default function GroupDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const term = useTerm();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast, showToast } = useToast(3500);

  const [group, setGroup] = useState(null);
  const [facets, setFacets] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/api/v1/assignment-groups/${id}/`);
      setGroup(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load group.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    getAdminAssignmentFacets().then(setFacets).catch(() => setFacets(null));
  }, []);

  if (loading) {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto">
        <LoadingState>Loading…</LoadingState>
      </main>
    );
  }
  if (error) {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto">
        <ErrorPanel>{error}</ErrorPanel>
      </main>
    );
  }
  if (!group) return null;

  const staffLabel = term(authorTermKey(group.group_type), { plural: true, capitalize: true });
  const staffLabelOne = term(authorTermKey(group.group_type));
  const membersLabel = term('camper', { plural: true, capitalize: true });
  const membersLabelOne = term('camper');
  const showSupervision = SUPERVISABLE_TYPES.has(group.group_type)
    && orgUsesSupervision(facets);

  const tabs = [
    { key: 'members', label: membersLabel },
    { key: 'staff', label: staffLabel },
    ...(showSupervision ? [{ key: 'supervision', label: 'Supervision' }] : []),
    { key: 'settings', label: 'Settings' },
  ];
  const requested = searchParams.get('tab');
  const activeTab = tabs.some((t) => t.key === requested) ? requested : 'members';
  const setTab = (key) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', key);
      return next;
    }, { replace: true });
  };

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid="admin-group-detail"
    >
      <PageHeader
        title={group.name}
        subtitle={[
          groupTypeLabel(group.group_type),
          group.parent_name ? `part of ${group.parent_name}` : null,
          group.program_name,
        ].filter(Boolean).join(' · ')}
        backTo="/admin/groups"
        backLabel={term('group', { plural: true, capitalize: true })}
        actions={(
          <>
            {!group.is_active && <Badge tone="neutral">Archived</Badge>}
            <Button
              variant="secondary"
              onClick={() => navigate(`/dashboards/subject-trends/${id}`)}
              data-testid="group-subject-trends-link"
            >
              <BarChart3 size={14} aria-hidden="true" />
              Trends
            </Button>
          </>
        )}
      />

      <nav
        className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-5"
        aria-label="Group sections"
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            data-testid={`group-tab-${t.key}`}
            aria-current={activeTab === t.key ? 'page' : undefined}
            className={`px-4 py-2 -mb-px text-sm font-semibold border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-blue-600 text-blue-700 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {activeTab === 'members' && (
        <GroupRosterTab
          group={group}
          roleInGroup="subject"
          roleLabel={{ one: membersLabelOne, other: membersLabel.toLowerCase() }}
          otherRoleLabel={staffLabel.toLowerCase()}
          emptyHint={`Add the ${membersLabel.toLowerCase()} this ${term('group')} is about. A group with no ${membersLabel.toLowerCase()} produces no logs.`}
          onChanged={load}
          showToast={showToast}
        />
      )}
      {activeTab === 'staff' && (
        <GroupRosterTab
          group={group}
          roleInGroup="author"
          roleLabel={{ one: staffLabelOne, other: staffLabel.toLowerCase() }}
          otherRoleLabel={membersLabel.toLowerCase()}
          emptyHint={`Nobody can write logs here until at least one ${staffLabelOne} is assigned.`}
          onChanged={load}
          showToast={showToast}
        />
      )}
      {activeTab === 'supervision' && (
        <GroupSupervisionTab group={group} onChanged={load} showToast={showToast} />
      )}
      {activeTab === 'settings' && (
        <GroupSettingsTab group={group} onChanged={load} showToast={showToast} />
      )}

      <Toast message={toast} />
    </main>
  );
}
