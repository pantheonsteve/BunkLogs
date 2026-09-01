/**
 * Setup — the once-a-year configuration that isn't day-to-day admin.
 *
 * Programs used to live inside Memberships, which put "delete the whole
 * school year" one click from a routine roster edit. They're their own
 * area now, and deletion sits behind the row's overflow menu with typed
 * confirmation.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { listAdminPrograms } from '../../../api/admin';
import {
  AddProgramModal,
  EditProgramModal,
  EndProgramModal,
  ViewProgramModal,
} from '../../../components/admin/ProgramAdminModals';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import Card, { CardBody, CardHeader } from '../../../components/ui/Card';
import DataTable from '../../../components/ui/DataTable';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import FilterBar, { FilterChips } from '../../../components/ui/FilterBar';
import LoadingState from '../../../components/ui/LoadingState';
import OverflowMenu, { OverflowMenuItem, OverflowMenuSeparator } from '../../../components/ui/OverflowMenu';
import PageHeader from '../../../components/ui/PageHeader';
import { useAdminProgram } from '../../../context/AdminProgramContext';
import { useTerm } from '../../../context/OrgBrandingContext';

const STATUS_FILTERS = [
  { value: 'active', label: 'Active' },
  { value: 'ended', label: 'Ended' },
  { value: 'all', label: 'All' },
];

export default function AdminSetupPage() {
  const term = useTerm();
  const { refresh: refreshProgramSwitcher } = useAdminProgram();
  const [programs, setPrograms] = useState([]);
  const [statusFilter, setStatusFilter] = useState('active');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null);

  const programsLo = term('program', { plural: true });
  const programLo = term('program');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listAdminPrograms();
      setPrograms(data.results || []);
    } catch (err) {
      setError(err?.response?.data?.detail || `Could not load ${programsLo}.`);
    } finally {
      setLoading(false);
    }
  }, [programsLo]);

  useEffect(() => { load(); }, [load]);

  const afterChange = () => {
    setModal(null);
    load();
    refreshProgramSwitcher?.();
  };

  const rows = programs.filter((p) => {
    if (statusFilter === 'active') return p.is_active;
    if (statusFilter === 'ended') return !p.is_active;
    return true;
  });

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (p) => (
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 dark:text-white">{p.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {p.program_type ? p.program_type.replace(/_/g, ' ') : 'no type set'}
          </p>
        </div>
      ),
    },
    {
      key: 'dates',
      header: 'Runs',
      render: (p) => (
        <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
          {p.start_date || '—'}{p.end_date ? ` → ${p.end_date}` : ''}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p) => (
        <Badge tone={p.is_active ? 'ok' : 'neutral'} dot>
          {p.is_active ? 'Active' : 'Ended'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (p) => (
        <OverflowMenu
          size="sm"
          label={`Actions for ${p.name}`}
          triggerTestId={`program-actions-${p.id}`}
        >
          <OverflowMenuItem
            onClick={() => setModal({ kind: 'view', program: p })}
            data-testid={`program-view-${p.id}`}
          >
            View details
          </OverflowMenuItem>
          <OverflowMenuItem
            onClick={() => setModal({ kind: 'edit', program: p })}
            data-testid={`program-edit-${p.id}`}
          >
            Edit
          </OverflowMenuItem>
          <OverflowMenuSeparator />
          <OverflowMenuItem
            danger
            disabled={!p.is_active}
            onClick={() => setModal({ kind: 'delete', program: p })}
            data-testid={`program-delete-${p.id}`}
          >
            {p.is_active ? `Delete ${p.name}…` : 'Already ended'}
          </OverflowMenuItem>
        </OverflowMenu>
      ),
    },
  ];

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid="admin-setup"
    >
      <PageHeader
        title={term('program', { plural: true, capitalize: true })}
        subtitle={`The ${programsLo} every roster, group and reflection hangs off.`}
        backTo="/admin/home"
        actions={(
          <Button onClick={() => setModal({ kind: 'add' })} data-testid="program-add">
            Add {programLo}
          </Button>
        )}
      />

      <Card>
        <CardHeader
          title={`All ${programsLo}`}
          action={(
            <FilterBar className="mb-0">
              <FilterChips
                value={statusFilter}
                onChange={setStatusFilter}
                options={STATUS_FILTERS}
                testIdPrefix="program-filter-"
              />
            </FilterBar>
          )}
        />
        <CardBody className="p-0">
          {loading ? (
            <div className="p-4"><LoadingState>Loading {programsLo}…</LoadingState></div>
          ) : error ? (
            <div className="p-4"><ErrorPanel>{error}</ErrorPanel></div>
          ) : (
            <DataTable
              className="border-0 rounded-none"
              columns={columns}
              rows={rows}
              rowTestId={(p) => `program-row-${p.id}`}
              empty={(
                <EmptyState title={`No ${programsLo} match this filter`}>
                  Add one to start enrolling people.
                </EmptyState>
              )}
              data-testid="program-list"
            />
          )}
        </CardBody>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Organization settings"
          subtitle="Vocabulary, notification defaults and integrations."
        />
        <CardBody>
          <Link
            to="/admin/settings"
            className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
          >
            Open settings
          </Link>
        </CardBody>
      </Card>

      {modal?.kind === 'add' && (
        <AddProgramModal onClose={() => setModal(null)} onCreated={afterChange} />
      )}
      {modal?.kind === 'view' && (
        <ViewProgramModal programId={modal.program.id} onClose={() => setModal(null)} />
      )}
      {modal?.kind === 'edit' && (
        <EditProgramModal
          programId={modal.program.id}
          onClose={() => setModal(null)}
          onSaved={afterChange}
        />
      )}
      {modal?.kind === 'delete' && (
        <EndProgramModal
          program={modal.program}
          onClose={() => setModal(null)}
          onEnded={afterChange}
        />
      )}
    </main>
  );
}
