import { useCallback, useEffect, useState } from 'react';
import {
  buildAdminPeopleListParams,
  getAdminPerson,
  inviteAdminPerson,
  listAdminPeople,
  listAdminPrograms,
} from '../../../api/admin';
import DeletePersonModal from '../../../components/admin/DeletePersonModal';
import PersonProfilePanel from '../../../components/admin/PersonProfilePanel';
import { writeStoredProgramId } from '../../../lib/adminProgramContext';
import ProgramListPane from './ProgramListPane';
import ProgramMembersPane from './ProgramMembersPane';

const PAGE_SIZE = 50;

export default function ProgramRosterTab() {
  const [programs, setPrograms] = useState([]);
  const [activePrograms, setActivePrograms] = useState([]);
  const [programsLoading, setProgramsLoading] = useState(true);
  const [programFilter, setProgramFilter] = useState('active');
  const [selectedProgramId, setSelectedProgramId] = useState(null);
  const [people, setPeople] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [peopleError, setPeopleError] = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [personLoading, setPersonLoading] = useState(false);
  const [invitedStatus, setInvitedStatus] = useState({});
  const [deletingPerson, setDeletingPerson] = useState(null);
  const [reloadRosterToken, setReloadRosterToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setProgramsLoading(true);
    Promise.all([
      listAdminPrograms(),
      listAdminPrograms('active'),
    ]).then(([all, active]) => {
      if (cancelled) return;
      setPrograms(all.results || []);
      setActivePrograms(active.results || []);
    }).finally(() => {
      if (!cancelled) setProgramsLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedProgramId) {
      setPeople([]);
      setTotalCount(0);
      return undefined;
    }

    const controller = new AbortController();
    let cancelled = false;

    const fetchPeople = async () => {
      setPeopleError(null);
      setPeopleLoading(true);
      try {
        const params = buildAdminPeopleListParams({
          program: selectedProgramId,
          search,
          offset,
          page_size: PAGE_SIZE,
        });
        const list = await listAdminPeople(params, { signal: controller.signal });
        if (cancelled) return;
        setPeople(list.results || []);
        setTotalCount(list.count ?? 0);
      } catch (err) {
        if (cancelled || err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return;
        setPeopleError(err);
      } finally {
        if (!cancelled) setPeopleLoading(false);
      }
    };

    fetchPeople();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedProgramId, search, offset, reloadRosterToken]);

  useEffect(() => {
    if (!selectedPersonId) {
      setSelectedPerson(null);
      return undefined;
    }

    let cancelled = false;
    setPersonLoading(true);
    getAdminPerson(selectedPersonId)
      .then((person) => {
        if (!cancelled) setSelectedPerson(person);
      })
      .catch(() => {
        if (!cancelled) {
          setSelectedPerson(null);
          setSelectedPersonId(null);
        }
      })
      .finally(() => {
        if (!cancelled) setPersonLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedPersonId]);

  const selectedProgram = programs.find(
    (p) => String(p.id) === String(selectedProgramId),
  ) || null;

  const handleSelectProgram = useCallback((programId) => {
    setSelectedProgramId(programId);
    setSelectedPersonId(null);
    setOffset(0);
    setSearch('');
    writeStoredProgramId(programId);
  }, []);

  const handleSearchChange = useCallback((value) => {
    setSearch(value);
    setOffset(0);
  }, []);

  const refreshPerson = useCallback((person) => {
    if (person?.id) {
      setSelectedPerson(person);
    } else if (selectedPersonId) {
      getAdminPerson(selectedPersonId).then(setSelectedPerson);
    }
    setReloadRosterToken((t) => t + 1);
  }, [selectedPersonId]);

  const handleInvite = async (personId) => {
    setInvitedStatus((prev) => ({ ...prev, [personId]: 'pending' }));
    try {
      await inviteAdminPerson(personId);
      setInvitedStatus((prev) => ({ ...prev, [personId]: 'sent' }));
    } catch {
      setInvitedStatus((prev) => ({ ...prev, [personId]: 'error' }));
    }
  };

  return (
    <div data-testid="membership-roster-tab">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ProgramListPane
          programs={programs}
          programFilter={programFilter}
          onProgramFilterChange={setProgramFilter}
          selectedProgramId={selectedProgramId}
          onSelectProgram={handleSelectProgram}
          loading={programsLoading}
        />

        <ProgramMembersPane
          program={selectedProgram}
          people={people}
          loading={peopleLoading}
          error={peopleError}
          search={search}
          onSearchChange={handleSearchChange}
          selectedPersonId={selectedPersonId}
          onSelectPerson={setSelectedPersonId}
          offset={offset}
          pageSize={PAGE_SIZE}
          totalCount={totalCount}
          onPrevious={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
          onNext={() => setOffset((prev) => prev + PAGE_SIZE)}
        />

        <aside
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4 min-h-[20rem]"
          data-testid="membership-person-drawer"
        >
          {!selectedPersonId ? (
            <p className="text-sm italic text-gray-500">Select a person to view their profile.</p>
          ) : personLoading || !selectedPerson ? (
            <p className="text-sm text-gray-500">Loading profile…</p>
          ) : (
            <div className="max-h-[70vh] overflow-y-auto">
              <PersonProfilePanel
                person={selectedPerson}
                programs={activePrograms}
                invitedStatus={invitedStatus}
                onInvite={handleInvite}
                onDelete={setDeletingPerson}
                onPersonChanged={refreshPerson}
              />
            </div>
          )}
        </aside>
      </div>

      {deletingPerson && (
        <DeletePersonModal
          person={deletingPerson}
          onClose={() => setDeletingPerson(null)}
          onCompleted={(result) => {
            setDeletingPerson(null);
            if (result?.person_id) {
              if (String(selectedPersonId) === String(result.person_id)) {
                setSelectedPersonId(null);
                setSelectedPerson(null);
              }
              setReloadRosterToken((t) => t + 1);
            }
          }}
        />
      )}
    </div>
  );
}
