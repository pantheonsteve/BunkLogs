/**
 * People — the one roster screen.
 *
 * This absorbed the old Memberships page: program rosters are this list
 * filtered by the header's program, and membership tagging is a bulk
 * action on a selection rather than its own tab. Rows carry the facts
 * the filters narrow on (role, groups, invite status) so filtering isn't
 * an act of faith, and clicking a row previews it while the checkbox
 * selects it — two different gestures for two different intents.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import {
  buildAdminPeopleListParams,
  bulkInviteAdminPeople,
  getAdminPerson,
  inviteAdminPerson,
  listAdminPeople,
  listAdminPrograms,
} from '../../api/admin';
import BulkImportModal from '../../components/admin/BulkImportModal';
import DedupePeopleModal from '../../components/admin/DedupePeopleModal';
import DeletePersonModal from '../../components/admin/DeletePersonModal';
import PersonProfilePanel, {
  MEMBERSHIP_ROLE_OPTIONS,
  PeopleListPagination,
} from '../../components/admin/PersonProfilePanel';
import Badge from '../../components/ui/Badge';
import BulkActionBar from '../../components/ui/BulkActionBar';
import Button from '../../components/ui/Button';
import Card, { CardBody } from '../../components/ui/Card';
import DataTable from '../../components/ui/DataTable';
import EmptyState from '../../components/ui/EmptyState';
import ErrorPanel from '../../components/ui/ErrorPanel';
import FilterBar, { FilterChips, FilterSelect, SearchInput } from '../../components/ui/FilterBar';
import LoadingState from '../../components/ui/LoadingState';
import Note from '../../components/ui/Note';
import OverflowMenu, { OverflowMenuItem } from '../../components/ui/OverflowMenu';
import PageHeader from '../../components/ui/PageHeader';
import { useAdminProgram } from '../../context/AdminProgramContext';
import { profileLink } from '../../utils/dashboardLinks';
import AddPersonModal from './people/AddPersonModal';
import BulkTagModal from './people/BulkTagModal';

const PAGE_SIZE_OPTIONS = [25, 50, 100];

const INVITE_FILTERS = [
  { value: '', label: 'Anyone' },
  { value: 'never', label: 'Never invited' },
  { value: 'invited', label: 'Awaiting sign-in' },
  { value: 'active', label: 'Signed in' },
];

const INVITE_BADGES = {
  active: { tone: 'ok', label: 'Signed in' },
  invited: { tone: 'warn', label: 'Invited' },
  never: { tone: 'neutral', label: 'Not invited' },
};

function relativeDay(iso) {
  if (!iso) return '—';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export default function AdminPeople() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { programId, program } = useAdminProgram();

  const [people, setPeople] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const inviteFilter = searchParams.get('invite_status') || '';
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [selectedPeople, setSelectedPeople] = useState(() => new Map());
  const [previewId, setPreviewId] = useState(null);
  const [previewPerson, setPreviewPerson] = useState(null);

  const [adding, setAdding] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deduping, setDeduping] = useState(false);
  const [tagging, setTagging] = useState(false);
  const [deletingPerson, setDeletingPerson] = useState(null);
  const [invitedStatus, setInvitedStatus] = useState({});
  const [bulkInviteResult, setBulkInviteResult] = useState(null);
  const [banner, setBanner] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const reloadPeople = () => setReloadToken((token) => token + 1);

  const setInviteFilter = (value) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set('invite_status', value);
      else next.delete('invite_status');
      return next;
    });
    setOffset(0);
  };

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const fetchPeople = async () => {
      setError(null);
      setLoading(true);
      try {
        const params = buildAdminPeopleListParams({
          search,
          role: roleFilter,
          status: statusFilter,
          invite_status: inviteFilter,
          program: programId,
          offset,
          page_size: pageSize,
        });
        const [list, progList] = await Promise.all([
          listAdminPeople(params, { signal: controller.signal }),
          listAdminPrograms('active'),
        ]);
        if (cancelled) return;
        setPeople(list.results || []);
        setTotalCount(list.count ?? 0);
        setPrograms(progList.results || []);
      } catch (err) {
        if (cancelled || err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return;
        setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPeople();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [search, roleFilter, statusFilter, inviteFilter, programId, offset, pageSize, reloadToken]);

  // Bulk actions act on whole records (memberships to tag, users to merge),
  // so a selection needs the full profile, not the list row.
  useEffect(() => {
    let cancelled = false;
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      setSelectedPeople(new Map());
      return undefined;
    }
    Promise.all(
      ids.map(async (id) => {
        try {
          return [id, await getAdminPerson(id)];
        } catch {
          return [id, null];
        }
      }),
    ).then((entries) => {
      if (cancelled) return;
      setSelectedPeople(new Map(entries.filter(([, person]) => person)));
    });
    return () => { cancelled = true; };
  }, [selectedIds]);

  useEffect(() => {
    let cancelled = false;
    if (previewId == null) {
      setPreviewPerson(null);
      return undefined;
    }
    getAdminPerson(previewId)
      .then((person) => { if (!cancelled) setPreviewPerson(person); })
      .catch(() => { if (!cancelled) setPreviewPerson(null); });
    return () => { cancelled = true; };
  }, [previewId, reloadToken]);

  const togglePerson = useCallback((personId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(personId)) next.delete(personId);
      else next.add(personId);
      return next;
    });
  }, []);

  const toggleAll = useCallback((checked) => {
    setSelectedIds(checked ? new Set(people.map((p) => p.id)) : new Set());
  }, [people]);

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectedPeople(new Map());
  };

  const refreshPreview = () => {
    if (previewId != null) getAdminPerson(previewId).then(setPreviewPerson);
    reloadPeople();
  };

  const handleInvite = async (personId) => {
    setInvitedStatus((prev) => ({ ...prev, [personId]: 'pending' }));
    try {
      await inviteAdminPerson(personId);
      setInvitedStatus((prev) => ({ ...prev, [personId]: 'sent' }));
      reloadPeople();
    } catch {
      setInvitedStatus((prev) => ({ ...prev, [personId]: 'error' }));
    }
  };

  const handleBulkInvite = async () => {
    setBulkInviteResult(null);
    try {
      const result = await bulkInviteAdminPeople(Array.from(selectedIds));
      setBulkInviteResult(result);
      clearSelection();
      reloadPeople();
    } catch (err) {
      setBanner({
        tone: 'danger',
        text: err?.response?.data?.detail || 'Could not send invitations.',
      });
    }
  };

  const selectedCount = selectedIds.size;
  const selectedProfiles = useMemo(
    () => Array.from(selectedIds).map((id) => selectedPeople.get(id)).filter(Boolean),
    [selectedIds, selectedPeople],
  );

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (p) => (
        <div className="min-w-0">
          <Link
            to={profileLink(p.id)}
            onClick={(e) => e.stopPropagation()}
            className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
          >
            {p.full_name}
          </Link>
          <p className="text-xs text-gray-500 dark:text-gray-400">{p.email || 'no email'}</p>
        </div>
      ),
    },
    {
      key: 'roles',
      header: 'Role',
      render: (p) => (
        (p.roles || []).length === 0
          ? <span className="text-gray-400">—</span>
          : (
            <div className="flex flex-wrap gap-1">
              {p.roles.map((r) => <Badge key={r} tone="info">{r.replace(/_/g, ' ')}</Badge>)}
            </div>
          )
      ),
    },
    {
      key: 'groups',
      header: 'Groups',
      render: (p) => (
        (p.groups || []).length === 0
          ? <span className="text-gray-400">—</span>
          : <span className="text-xs">{p.groups.join(' · ')}</span>
      ),
    },
    {
      key: 'invite',
      header: 'Access',
      render: (p) => {
        const badge = INVITE_BADGES[p.invite_status] || INVITE_BADGES.never;
        return <Badge tone={badge.tone} dot>{badge.label}</Badge>;
      },
    },
    {
      key: 'last_active',
      header: 'Last active',
      align: 'right',
      render: (p) => (
        <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
          {relativeDay(p.last_login)}
        </span>
      ),
    },
  ];

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid="admin-people"
    >
      <PageHeader
        title="People"
        subtitle={
          program
            ? `Everyone in ${program.name}`
            : 'Everyone in this organization, across all programs'
        }
        actions={(
          <>
            <Button
              variant="secondary"
              data-testid="open-bulk-import"
              onClick={() => setImporting(true)}
            >
              Bulk import
            </Button>
            <Button data-testid="open-add-person" onClick={() => setAdding(true)}>
              Add person
            </Button>
          </>
        )}
      />

      <FilterBar>
        <SearchInput
          value={search}
          onChange={(v) => { setSearch(v); setOffset(0); }}
          placeholder="Search name or email…"
          data-testid="people-search"
        />
        <FilterSelect
          value={roleFilter}
          onChange={(v) => { setRoleFilter(v); setOffset(0); }}
          data-testid="people-role-filter"
          options={[
            { value: '', label: 'Any role' },
            ...MEMBERSHIP_ROLE_OPTIONS.map((r) => ({ value: r, label: r.replace(/_/g, ' ') })),
          ]}
        />
        <FilterSelect
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setOffset(0); }}
          data-testid="people-status-filter"
          options={[
            { value: 'active', label: 'Active' },
            { value: 'inactive', label: 'Inactive' },
            { value: '', label: 'Any status' },
          ]}
        />
        <FilterChips
          value={inviteFilter}
          onChange={setInviteFilter}
          testIdPrefix="people-invite-filter-"
          options={INVITE_FILTERS}
        />
        <div className="flex-1" />
        <FilterSelect
          value={String(pageSize)}
          onChange={(v) => { setPageSize(Number(v)); setOffset(0); }}
          data-testid="people-page-size"
          options={PAGE_SIZE_OPTIONS.map((n) => ({ value: String(n), label: `${n} per page` }))}
        />
      </FilterBar>

      {banner && <div className="mb-4"><Note tone={banner.tone}>{banner.text}</Note></div>}

      {bulkInviteResult && (
        <div className="mb-4">
          <Note
            tone={bulkInviteResult.skipped_count > 0 ? 'warn' : 'ok'}
            title={`${bulkInviteResult.sent_count} invitation${bulkInviteResult.sent_count === 1 ? '' : 's'} sent`}
            data-testid="bulk-invite-result"
          >
            {bulkInviteResult.skipped_count > 0 ? (
              <ul className="mt-1 list-disc pl-5 space-y-0.5">
                {bulkInviteResult.skipped.map((s) => (
                  <li key={s.person_id}>{s.name || `Person ${s.person_id}`} — {s.reason}</li>
                ))}
              </ul>
            ) : (
              <p>Everyone selected now has a login on the way.</p>
            )}
          </Note>
        </div>
      )}

      <BulkActionBar count={selectedCount} onClear={clearSelection}>
        <Button size="sm" onClick={handleBulkInvite} data-testid="bulk-invite">
          Send {selectedCount} invitation{selectedCount === 1 ? '' : 's'}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setTagging(true)}
          data-testid="open-bulk-tag"
        >
          Tag memberships
        </Button>
        <OverflowMenu size="sm" label="More bulk actions" triggerTestId="people-bulk-overflow">
          <OverflowMenuItem
            danger
            disabled={selectedCount < 2}
            onClick={() => setDeduping(true)}
            data-testid="open-dedupe"
          >
            {selectedCount < 2
              ? 'Merge duplicates (select two or more)'
              : `Merge ${selectedCount} records into one…`}
          </OverflowMenuItem>
        </OverflowMenu>
      </BulkActionBar>

      {loading ? (
        <LoadingState>Loading people…</LoadingState>
      ) : error ? (
        <ErrorPanel>Could not load people.</ErrorPanel>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2">
            <DataTable
              columns={columns}
              rows={people}
              rowTestId={(p) => `person-row-${p.id}`}
              onRowClick={(p) => setPreviewId(p.id)}
              selection={{
                selected: selectedIds,
                onToggle: togglePerson,
                onToggleAll: toggleAll,
              }}
              empty={(
                <EmptyState title="Nobody matches those filters">
                  Widen the search, or add someone with the button above.
                </EmptyState>
              )}
              data-testid="people-list"
            />
            <PeopleListPagination
              offset={offset}
              resultCount={people.length}
              totalCount={totalCount}
              loading={loading}
              onPrevious={() => setOffset((prev) => Math.max(0, prev - pageSize))}
              onNext={() => setOffset((prev) => prev + pageSize)}
            />
          </div>

          <aside data-testid="person-drawer">
            {previewPerson ? (
              <PersonProfilePanel
                person={previewPerson}
                programs={programs}
                invitedStatus={invitedStatus}
                onInvite={handleInvite}
                onDelete={setDeletingPerson}
                onPersonChanged={refreshPreview}
                onDismiss={() => setPreviewId(null)}
              />
            ) : (
              <Card>
                <CardBody>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Click a row to preview that person. Use the checkboxes to
                    invite, tag or merge several at once.
                  </p>
                </CardBody>
              </Card>
            )}
          </aside>
        </div>
      )}

      {adding && (
        <AddPersonModal
          programs={programs}
          defaultProgramId={programId}
          onClose={() => setAdding(false)}
          onCreated={(person) => {
            setAdding(false);
            reloadPeople();
            if (person?.id) setPreviewId(person.id);
          }}
        />
      )}
      {deduping && (
        <DedupePeopleModal
          selectedPeople={selectedPeople}
          onClose={() => setDeduping(false)}
          onCompleted={(result) => {
            setDeduping(false);
            clearSelection();
            reloadPeople();
            if (result?.winner_id) setPreviewId(result.winner_id);
          }}
        />
      )}
      {tagging && (
        <BulkTagModal
          people={selectedProfiles}
          programId={programId}
          programName={program?.name}
          onClose={() => setTagging(false)}
          onApplied={(updated) => {
            setTagging(false);
            setBanner({
              tone: 'ok',
              text: `Updated tags on ${updated} membership${updated === 1 ? '' : 's'}.`,
            });
            reloadPeople();
          }}
        />
      )}
      {deletingPerson && (
        <DeletePersonModal
          person={deletingPerson}
          onClose={() => setDeletingPerson(null)}
          onCompleted={(result) => {
            setDeletingPerson(null);
            reloadPeople();
            if (result?.person_id) {
              if (String(previewId) === String(result.person_id)) setPreviewId(null);
              setSelectedIds((prev) => {
                const next = new Set(prev);
                next.delete(result.person_id);
                return next;
              });
            }
          }}
        />
      )}
      {importing && (
        <BulkImportModal
          programs={programs}
          onClose={() => { setImporting(false); reloadPeople(); }}
        />
      )}
    </main>
  );
}
