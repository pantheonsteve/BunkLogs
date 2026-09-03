/**
 * The one program (school year / season) every admin screen is scoped to.
 *
 * Before this provider each admin page fetched the program list and owned
 * its own selector, so Groups, Assignments and Memberships could disagree
 * about which program you were looking at and pages defaulted differently
 * — the main source of "why is this list empty".
 *
 * Resolution order is unchanged from `lib/adminProgramContext`: `?program=`
 * wins, then the session-stored id, then the newest active program. The URL
 * stays authoritative so an admin link can still deep-link a program.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useSearchParams } from 'react-router-dom';

import { listAdminPrograms } from '../api/admin';
import {
  readStoredProgramId,
  resolveInitialProgramId,
  writeStoredProgramId,
} from '../lib/adminProgramContext';

const AdminProgramContext = createContext(null);

// Outside the provider there is no program to resolve, so `ready` is true:
// consumers gate their fetches on it, and "no provider" must mean "carry on
// unscoped" rather than "wait forever".
const EMPTY = Object.freeze({
  programs: [],
  programId: '',
  program: null,
  ready: true,
  error: '',
  setProgramId: () => {},
  refresh: () => {},
});

export function AdminProgramProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [programs, setPrograms] = useState([]);
  const [programId, setProgramIdState] = useState('');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');

  const urlProgramId = searchParams.get('program');

  const setProgramId = useCallback(
    (nextId) => {
      const value = nextId ? String(nextId) : '';
      setProgramIdState(value);
      writeStoredProgramId(value);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value) next.set('program', value);
          else next.delete('program');
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // Setup can add or end a program, so the switcher has to be able to
  // re-read the list without a full page reload.
  const refresh = useCallback(() => {
    listAdminPrograms()
      .then((data) => setPrograms(data?.results || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    listAdminPrograms()
      .then((data) => {
        if (cancelled) return;
        const list = data?.results || [];
        setPrograms(list);
        const initial = resolveInitialProgramId({
          urlProgramId,
          storedProgramId: readStoredProgramId(),
          programs: list,
        });
        if (initial) {
          setProgramIdState(initial);
          writeStoredProgramId(initial);
          if (!urlProgramId) {
            setSearchParams(
              (prev) => {
                const next = new URLSearchParams(prev);
                next.set('program', initial);
                return next;
              },
              { replace: true },
            );
          }
        }
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        // A non-admin landing on an admin route still renders the shell;
        // pages handle their own 403s.
        setError('Could not load programs.');
        setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      programs,
      programId,
      program: programs.find((p) => String(p.id) === String(programId)) || null,
      ready,
      error,
      setProgramId,
      refresh,
    }),
    [programs, programId, ready, error, setProgramId, refresh],
  );

  return (
    <AdminProgramContext.Provider value={value}>{children}</AdminProgramContext.Provider>
  );
}

export function useAdminProgram() {
  return useContext(AdminProgramContext) || EMPTY;
}
