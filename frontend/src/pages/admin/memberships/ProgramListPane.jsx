import { useMemo, useState } from 'react';
import Button from '../../../components/ui/Button';
import {
  AddProgramModal,
  EditProgramModal,
  EndProgramModal,
  ViewProgramModal,
} from '../../../components/admin/ProgramAdminModals';

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'ended', label: 'Ended' },
];

export default function ProgramListPane({
  programs,
  programFilter,
  onProgramFilterChange,
  selectedProgramId,
  onSelectProgram,
  loading,
  onProgramsChanged,
}) {
  const [programModal, setProgramModal] = useState(null);
  const filteredPrograms = useMemo(() => {
    if (programFilter === 'active') {
      return programs.filter((p) => p.is_active);
    }
    if (programFilter === 'ended') {
      return programs.filter((p) => !p.is_active);
    }
    return programs;
  }, [programs, programFilter]);

  const selectedProgram = programs.find(
    (p) => String(p.id) === String(selectedProgramId),
  ) || null;
  const canActOnProgram = Boolean(selectedProgram);

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3 space-y-2 min-h-[20rem] flex flex-col">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Programs</h2>
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden text-xs">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              data-testid={`membership-program-filter-${opt.key}`}
              onClick={() => onProgramFilterChange(opt.key)}
              className={[
                'px-2 py-1 transition-colors',
                programFilter === opt.key
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5" data-testid="membership-program-actions">
        <Button size="sm" onClick={() => setProgramModal('add')} data-testid="membership-program-add">
          Add Program
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={!canActOnProgram}
          onClick={() => setProgramModal('view')}
          data-testid="membership-program-view"
        >
          View Program
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={!canActOnProgram}
          onClick={() => setProgramModal('edit')}
          data-testid="membership-program-edit"
        >
          Edit Program
        </Button>
        <Button
          size="sm"
          variant="danger"
          disabled={!canActOnProgram || !selectedProgram?.is_active}
          onClick={() => setProgramModal('delete')}
          data-testid="membership-program-delete"
        >
          Delete Program
        </Button>
      </div>
      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : filteredPrograms.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 py-4">No programs match this filter.</p>
      ) : (
        <ul className="flex-1 overflow-y-auto max-h-96 space-y-1" data-testid="membership-program-list">
          {filteredPrograms.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                data-testid={`membership-program-${p.id}`}
                onClick={() => onSelectProgram(p.id)}
                className={[
                  'w-full text-left rounded-lg px-3 py-2 text-sm transition-colors',
                  String(selectedProgramId) === String(p.id)
                    ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-100 font-medium'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200',
                ].join(' ')}
              >
                <span className="block font-medium">{p.name}</span>
                <span className="block text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {p.is_active ? 'Active' : 'Ended'}
                  {p.start_date ? ` · ${p.start_date}` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {programModal === 'add' && (
        <AddProgramModal
          onClose={() => setProgramModal(null)}
          onCreated={(created) => {
            setProgramModal(null);
            onProgramsChanged?.(created);
            if (created?.id) {
              onSelectProgram(created.id);
            }
          }}
        />
      )}
      {programModal === 'view' && selectedProgramId && (
        <ViewProgramModal
          programId={selectedProgramId}
          onClose={() => setProgramModal(null)}
        />
      )}
      {programModal === 'edit' && selectedProgramId && (
        <EditProgramModal
          programId={selectedProgramId}
          onClose={() => setProgramModal(null)}
          onSaved={(updated) => {
            setProgramModal(null);
            onProgramsChanged?.(updated);
            if (updated?.id) {
              onSelectProgram(updated.id);
            }
          }}
        />
      )}
      {programModal === 'delete' && selectedProgram && (
        <EndProgramModal
          program={selectedProgram}
          onClose={() => setProgramModal(null)}
          onEnded={() => {
            setProgramModal(null);
            onProgramsChanged?.();
          }}
        />
      )}
    </section>
  );
}
