/**
 * Cohort feed — Step 4_9 §4.5.
 *
 * Posts are excerpts Madrichim explicitly chose to share from a reflection
 * field flagged `share_with_cohort`; nothing lands here implicitly. Likes are
 * the only reaction, and you cannot like your own post.
 *
 * Also serves faculty and the Director, who see the classrooms they supervise
 * and can hide a post; the backend decides which, and `can_hide` gates the UI.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, MessageCircle } from 'lucide-react';
import {
  fetchCohortFeed, fetchCohortMembers, setShareHidden, toggleShareLike,
} from '../../api/threads';
import { useAuth } from '../../auth/AuthContext';
import { useTerm } from '../../context/OrgBrandingContext';
import BackLink from '../../components/ui/BackLink';
import CardSkeleton from '../../components/ui/CardSkeleton';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import RichText from '../../components/ui/RichText';
import UnreadDot from '../../components/ui/UnreadDot';
import { hasCapability, membershipRolesForUser } from '../../utils/auth/capability';
import { initialsFor } from '../../utils/initials';

const AVATAR_COLORS = [
  'bg-violet-600',
  'bg-indigo-600',
  'bg-sky-600',
  'bg-emerald-600',
  'bg-amber-600',
  'bg-rose-600',
];
const VISIBLE_AVATARS = 6;
const FOCUS_RING = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600';

function avatarColor(id) {
  const n = Math.abs(Number(id) || 0);
  return AVATAR_COLORS[n % AVATAR_COLORS.length];
}

function backHomePath(user) {
  if (hasCapability(user, 'admin')) return '/admin/home';
  const roles = membershipRolesForUser(user);
  if (roles.includes('faculty') && !roles.includes('madrich')) return '/faculty';
  return '/madrich';
}

function RosterRow({ members, onViewAll }) {
  if (!members || members.length === 0) return null;
  const shown = members.slice(0, VISIBLE_AVATARS);
  const extra = members.length - shown.length;
  const noun = members.length === 1 ? 'Madrich' : 'Madrichim';
  const label = `${members.length} ${noun}, view all`;
  return (
    <button
      type="button"
      onClick={onViewAll}
      aria-label={label}
      data-testid="md-cohort-members"
      className={`flex max-w-full flex-wrap items-center gap-3 rounded-lg text-left ${FOCUS_RING}`}
    >
      <span className="flex items-center pl-1">
        {shown.map((member) => (
          <span
            key={member.id}
            className={`-ml-1 inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white ring-2 ring-white dark:ring-gray-900 ${avatarColor(member.id)}`}
          >
            {member.initials}
          </span>
        ))}
        {extra > 0 && (
          <span className="-ml-1 inline-flex h-8 min-w-8 items-center justify-center rounded-full bg-gray-200 px-1.5 text-xs font-semibold text-gray-700 ring-2 ring-white dark:bg-gray-700 dark:text-gray-100 dark:ring-gray-900">
            +{extra}
          </span>
        )}
      </span>
      <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
        {members.length} {noun} · View all
      </span>
    </button>
  );
}

function RosterModal({ members, onClose }) {
  const [query, setQuery] = useState('');
  const needle = query.trim().toLowerCase();
  const groups = useMemo(() => {
    const matching = members.filter((member) => (
      !needle || (member.display_name || '').toLowerCase().includes(needle)
    ));
    const byName = new Map();
    matching.forEach((member) => {
      const name = member.cohort?.name || 'Teaching team';
      if (!byName.has(name)) byName.set(name, []);
      byName.get(name).push(member);
    });
    return [...byName.entries()];
  }, [members, needle]);

  return (
    <Modal title="Madrichim" onClose={onClose} data-testid="md-cohort-roster-modal">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
        Search
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          data-testid="md-cohort-roster-search"
          className={`mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm ${FOCUS_RING}`}
        />
      </label>
      {groups.length === 0 ? (
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">No matches.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {groups.map(([name, people]) => (
            <section key={name}>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {name}
              </h3>
              <ul className="mt-2 space-y-1">
                {people.map((member) => (
                  <li key={member.id} className="flex items-center gap-2 text-sm text-gray-900 dark:text-white">
                    <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white ${avatarColor(member.id)}`}>
                      {member.initials}
                    </span>
                    {member.display_name}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </Modal>
  );
}

function Post({ post, onLike, onRequestHide }) {
  const [pending, setPending] = useState(false);
  const term = useTerm();

  async function act(fn) {
    setPending(true);
    try {
      await fn();
    } finally {
      setPending(false);
    }
  }

  return (
    <article
      className={`rounded-xl border-l-4 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm ${
        post.is_hidden
          ? 'border-l-rose-500 bg-rose-50/60 dark:bg-rose-900/15'
          : 'border-l-indigo-500 dark:border-l-indigo-400'
      }`}
      data-testid={`cohort-post-${post.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`inline-flex items-center justify-center h-8 w-8 rounded-full text-xs font-bold text-white shrink-0 ${avatarColor(post.author?.id)}`}>
            {initialsFor(post.author?.display_name)}
          </span>
          <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
            {post.author?.display_name}
            {post.is_mine && (
              <span className="ml-2 text-xs font-medium text-indigo-700 dark:text-indigo-300">you</span>
            )}
          </p>
        </div>
        {post.unread && <UnreadDot label="New activity" />}
      </div>

      {post.is_hidden && (
        <p
          className="mt-2 inline-block text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200"
          data-testid={`cohort-hidden-${post.id}`}
        >
          {`Hidden from the ${term('cohort')}.`}
        </p>
      )}

      <RichText
        html={post.body}
        as="div"
        className="mt-2 text-sm text-gray-800 dark:text-gray-100"
      />

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <button
          type="button"
          disabled={!post.can_like || pending}
          onClick={() => act(() => onLike(post.id))}
          data-testid={`cohort-like-${post.id}`}
          title={post.can_like ? undefined : 'You cannot like your own post'}
          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 border font-medium transition-colors ${FOCUS_RING} ${
            post.liked_by_me
              ? 'border-violet-600 bg-violet-600 text-white hover:bg-violet-700'
              : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:border-violet-400 hover:text-violet-700 dark:hover:text-violet-300'
          } disabled:opacity-40 disabled:hover:border-gray-300`}
        >
          <Heart
            size={15}
            aria-hidden="true"
            fill={post.liked_by_me ? 'currentColor' : 'none'}
          />
          <span>{post.like_count}</span>
          <span className="sr-only">
            {post.liked_by_me ? 'Remove like' : 'Like this post'}
          </span>
        </button>

        {post.thread_id && (
          <Link
            to={`/madrich/threads/${post.thread_id}`}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 border border-gray-300 dark:border-gray-600 font-medium text-indigo-700 dark:text-indigo-300 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/25 transition-colors ${FOCUS_RING}`}
            data-testid={`cohort-comments-${post.id}`}
          >
            <MessageCircle size={15} aria-hidden="true" />
            {post.comment_count === 0
              ? 'Comment'
              : `${post.comment_count} comment${post.comment_count === 1 ? '' : 's'}`}
          </Link>
        )}

        {post.can_hide && (
          <button
            type="button"
            disabled={pending}
            onClick={() => onRequestHide(post)}
            data-testid={`cohort-hide-${post.id}`}
            aria-label={post.is_hidden ? 'Unhide this post' : 'Hide this post'}
            className={`ml-auto rounded-lg px-2.5 py-1 font-medium text-gray-700 dark:text-gray-200 hover:text-rose-700 dark:hover:text-rose-300 hover:underline disabled:opacity-40 ${FOCUS_RING}`}
          >
            {post.is_hidden ? 'Unhide' : 'Hide'}
          </button>
        )}
      </div>
    </article>
  );
}

const VISIBILITY = [
  ['all', 'All'],
  ['visible', 'Visible'],
  ['hidden', 'Hidden'],
];

export default function MadrichCohortFeed() {
  const { orgSlug, user } = useAuth();
  const term = useTerm();
  const isAdmin = hasCapability(user, 'admin');
  const [feed, setFeed] = useState(null);
  const [members, setMembers] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [groupId, setGroupId] = useState('');
  const [visibility, setVisibility] = useState('all');
  const [rosterOpen, setRosterOpen] = useState(false);
  const [pendingHide, setPendingHide] = useState(null);
  const [error, setError] = useState(null);
  const backTo = backHomePath(user);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [feedData, memberData] = await Promise.all([
        fetchCohortFeed(orgSlug, { group: groupId || undefined }),
        fetchCohortMembers(orgSlug).catch(() => ({ results: [], cohorts: [] })),
      ]);
      setFeed(feedData);
      setMembers(memberData?.results || []);
      setCohorts(memberData?.cohorts || []);
    } catch {
      setError(`Could not load the ${term('cohort')} feed.`);
    }
  }, [orgSlug, term, groupId]);

  useEffect(() => { load(); }, [load]);

  const handleLike = useCallback(async (shareId) => {
    await toggleShareLike(orgSlug, shareId);
    await load();
  }, [orgSlug, load]);

  const handleHide = useCallback(async (shareId, hidden) => {
    await setShareHidden(orgSlug, shareId, hidden);
    setPendingHide(null);
    await load();
  }, [orgSlug, load]);

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto overflow-x-hidden" data-testid="md-cohort-error">
        <BackLink to={backTo} label="Back to home" className="mb-2" data-testid="md-cohort-back" />
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button type="button" onClick={load} className={`mt-3 text-sm text-indigo-700 dark:text-indigo-300 underline ${FOCUS_RING}`}>
          Retry
        </button>
      </div>
    );
  }

  const posts = feed?.results || [];
  const shown = !isAdmin ? posts : posts.filter((post) => {
    if (visibility === 'visible') return !post.is_hidden;
    if (visibility === 'hidden') return post.is_hidden;
    return true;
  });

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4 overflow-x-hidden">
      <div>
        <BackLink to={backTo} label="Back to home" data-testid="md-cohort-back" />
        <div className="mt-2 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-4 shadow-md">
          <h1 className="text-xl font-bold text-white">{`My ${term('cohort')}`}</h1>
          <p className="text-sm text-violet-50">
            Ideas Madrichim chose to share from their reflections.
          </p>
        </div>
      </div>

      <RosterRow members={members} onViewAll={() => setRosterOpen(true)} />

      {isAdmin && cohorts.length > 1 && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Cohort
          <select
            value={groupId}
            onChange={(event) => setGroupId(event.target.value)}
            data-testid="md-cohort-picker"
            className={`mt-1 block w-full max-w-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm ${FOCUS_RING}`}
          >
            <option value="">All cohorts</option>
            {cohorts.map((cohort) => (
              <option key={cohort.id} value={cohort.id}>{cohort.name}</option>
            ))}
          </select>
        </label>
      )}

      {isAdmin && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Post visibility">
          {VISIBILITY.map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={visibility === value}
              onClick={() => setVisibility(value)}
              data-testid={`md-cohort-filter-${value}`}
              className={`rounded-full px-3 py-1 text-sm font-medium border ${FOCUS_RING} ${
                visibility === value
                  ? 'border-indigo-600 bg-indigo-600 text-white'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {!feed ? (
        <CardSkeleton rows={4} data-testid="md-cohort-loading" />
      ) : shown.length === 0 ? (
        posts.length > 0 ? (
          <EmptyState title="No posts in this view" data-testid="md-cohort-empty" />
        ) : (
          <EmptyState
            title={isAdmin ? 'Nothing shared yet' : 'No posts yet'}
            data-testid="md-cohort-empty"
            action={!isAdmin && (
              <Link
                to="/madrich/reflection/new"
                className={`text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline ${FOCUS_RING}`}
                data-testid="md-cohort-share-cta"
              >
                Share an idea from your weekly reflection →
              </Link>
            )}
          >
            {isAdmin
              ? 'Madrichim can share ideas from their weekly reflection.'
              : 'When someone shares an idea, it shows up here.'}
          </EmptyState>
        )
      ) : (
        <div className="space-y-3" data-testid="md-cohort-list">
          {shown.map((post) => (
            <Post
              key={post.id}
              post={post}
              onLike={handleLike}
              onRequestHide={setPendingHide}
            />
          ))}
        </div>
      )}

      {rosterOpen && (
        <RosterModal members={members} onClose={() => setRosterOpen(false)} />
      )}

      {pendingHide && (
        <ConfirmDialog
          title={pendingHide.is_hidden ? 'Unhide this post?' : 'Hide this post?'}
          description={
            pendingHide.is_hidden
              ? 'Madrichim will see it in the feed again.'
              : 'Madrichim will no longer see this post. You can put it back.'
          }
          confirmLabel={pendingHide.is_hidden ? 'Unhide' : 'Hide'}
          tone={pendingHide.is_hidden ? 'primary' : 'danger'}
          onConfirm={() => handleHide(pendingHide.id, !pendingHide.is_hidden)}
          onClose={() => setPendingHide(null)}
        />
      )}
    </div>
  );
}
