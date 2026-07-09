import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../auth/AuthContext';
import { homePathForUser } from '../utils/auth/capability';
import {
  clearImpersonationState,
  getImpersonationMeta,
  getOriginalSession,
  isImpersonating,
  markImpersonationActive,
  saveOriginalSession,
} from './impersonationStorage';

function displayName(user) {
  const name = `${user.first_name || ''} ${user.last_name || ''}`.trim();
  return name || user.name || user.email;
}

export default function DevImpersonation() {
  const { login, logout } = useAuth();
  const navigate = useNavigate();
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [impersonating, setImpersonating] = useState(isImpersonating());
  const [meta, setMeta] = useState(getImpersonationMeta());

  useEffect(() => {
    if (!import.meta.env.DEV) return undefined;

    let cancelled = false;
    api.get('/api/dev/impersonate/status/')
      .then((response) => {
        if (!cancelled && response.data?.enabled) {
          setEnabled(true);
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  const loadUsers = useCallback(async (search) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/dev/impersonate/users/', {
        params: search ? { q: search } : undefined,
      });
      setUsers(response.data?.results || []);
    } catch (requestError) {
      setUsers([]);
      setError('Could not load users.');
      console.warn('Dev impersonation user search failed:', requestError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled || !open) return undefined;

    const timer = setTimeout(() => {
      loadUsers(query.trim());
    }, 250);

    return () => clearTimeout(timer);
  }, [enabled, open, query, loadUsers]);

  const handleImpersonate = async (targetUser) => {
    setLoading(true);
    setError('');
    try {
      saveOriginalSession();
      const response = await api.post('/api/dev/impersonate/', {
        user_id: targetUser.id,
      });
      const profile = await login({
        access_token: response.data.access,
        refresh_token: response.data.refresh,
        user: response.data.user,
      });
      markImpersonationActive(profile);
      setImpersonating(true);
      setMeta(getImpersonationMeta());
      setOpen(false);
      navigate(homePathForUser(profile), { replace: true });
    } catch (requestError) {
      setError('Impersonation failed.');
      console.warn('Dev impersonation login failed:', requestError);
    } finally {
      setLoading(false);
    }
  };

  const handleExit = async () => {
    const original = getOriginalSession();
    clearImpersonationState();
    setImpersonating(false);
    setMeta(null);

    if (original.access_token) {
      const tokens = { access_token: original.access_token };
      if (original.refresh_token) {
        tokens.refresh_token = original.refresh_token;
      }
      if (original.user_profile) {
        try {
          tokens.user_profile = JSON.parse(original.user_profile);
        } catch {
          // Fall back to profile fetch via login().
        }
      }
      const profile = await login(tokens);
      navigate(homePathForUser(profile), { replace: true });
      return;
    }

    await logout();
    navigate('/signin', { replace: true });
  };

  if (!import.meta.env.DEV || !enabled) {
    return null;
  }

  return (
    <>
      {impersonating && meta ? (
        <div
          data-testid="dev-impersonation-banner"
          className="fixed top-0 inset-x-0 z-[60] flex items-center justify-center gap-3 bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950 shadow"
        >
          <span>
            Viewing as {meta.name} ({meta.role || 'no role'})
          </span>
          <button
            type="button"
            onClick={handleExit}
            className="rounded bg-amber-950 px-3 py-1 text-xs font-semibold text-amber-50 hover:bg-amber-900"
          >
            Exit impersonation
          </button>
        </div>
      ) : null}

      {!open ? (
        <button
          type="button"
          data-testid="dev-impersonation-toggle"
          onClick={() => setOpen(true)}
          className="fixed bottom-4 left-4 z-50 rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white shadow-lg hover:bg-violet-600"
        >
          Dev: view as user
        </button>
      ) : (
        <div
          data-testid="dev-impersonation-panel"
          className="fixed bottom-4 left-4 z-50 w-[22rem] max-h-[28rem] overflow-hidden rounded-lg border border-gray-700 bg-gray-900 text-white shadow-2xl"
        >
          <div className="flex items-center justify-between border-b border-gray-700 px-3 py-2">
            <span className="text-sm font-semibold">View as user</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-gray-400 hover:text-white"
              aria-label="Close"
            >
              ×
            </button>
          </div>

          <div className="p-3">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by email or name"
              className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white placeholder:text-gray-400"
            />
            {error ? (
              <p className="mt-2 text-xs text-red-300">{error}</p>
            ) : null}
          </div>

          <div className="max-h-64 overflow-y-auto border-t border-gray-700">
            {loading ? (
              <p className="px-3 py-4 text-xs text-gray-400">Loading users…</p>
            ) : null}
            {!loading && users.length === 0 ? (
              <p className="px-3 py-4 text-xs text-gray-400">No users found.</p>
            ) : null}
            {users.map((user) => (
              <button
                key={user.id}
                type="button"
                onClick={() => handleImpersonate(user)}
                className="block w-full border-b border-gray-800 px-3 py-2 text-left hover:bg-gray-800"
              >
                <div className="text-sm font-medium">{displayName(user)}</div>
                <div className="text-xs text-gray-400">{user.email}</div>
                <div className="text-xs text-violet-300">
                  {user.role || 'No legacy role'}
                  {user.membership_roles?.length
                    ? ` · ${user.membership_roles.join(', ')}`
                    : ''}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
