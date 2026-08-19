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
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, MessageCircle, Users } from 'lucide-react';
import {
  fetchCohortFeed, fetchCohortMembers, setShareHidden, toggleShareLike,
} from '../../api/threads';
import { useAuth } from '../../auth/AuthContext';
import BackLink from '../../components/ui/BackLink';
import CardSkeleton from '../../components/ui/CardSkeleton';
import EmptyState from '../../components/ui/EmptyState';
import HomeCard from '../../components/ui/HomeCard';
import RichText from '../../components/ui/RichText';
import UnreadDot from '../../components/ui/UnreadDot';
import { hasCapability, membershipRolesForUser } from '../../utils/auth/capability';
import { initialsFor } from '../../utils/initials';

/**
 * Where "back" goes for whoever is reading the feed. The Director arrives from
 * Admin Home; a Madrich from their own dashboard. `/madrich` is the fallback
 * because this is a Madrich surface first.
 */
function backHomePath(user) {
  if (hasCapability(user, 'admin')) return '/admin/home';
  const roles = membershipRolesForUser(user);
  if (roles.includes('faculty') && !roles.includes('madrich')) return '/faculty';
  return '/madrich';
}

function MembersCard({ members }) {
  if (!members || members.length === 0) return null;
  return (
    <HomeCard
      title="My cohort"
      subtitle={`${members.length} classmate${members.length === 1 ? '' : 's'}`}
      accent="violet"
      icon={Users}
      data-testid="md-cohort-members"
    >
      <ul className="flex flex-wrap gap-2">
        {members.map((m) => (
          <li
            key={m.id}
            className="inline-flex items-center gap-2 rounded-full border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-900/25 pl-1 pr-3 py-1"
          >
            <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-violet-600 text-xs font-bold text-white">
              {m.initials}
            </span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {m.display_name}
              {typeof m.grade_level === 'number' && (
                <span className="font-normal text-gray-600 dark:text-gray-300"> · {m.grade_level}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </HomeCard>
  );
}

function Post({ post, onLike, onHide }) {
  const [pending, setPending] = useState(false);

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
          <span className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-indigo-600 text-xs font-bold text-white shrink-0">
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
          Hidden from the cohort.
        </p>
      )}

      {/* Shared excerpts come from a rich_text reflection answer, so the stored
          value is Quill HTML rather than plain text. */}
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
          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 border font-medium transition-colors ${
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
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 border border-gray-300 dark:border-gray-600 font-medium text-indigo-700 dark:text-indigo-300 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/25 transition-colors"
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
            onClick={() => act(() => onHide(post.id, !post.is_hidden))}
            data-testid={`cohort-hide-${post.id}`}
            className="ml-auto rounded-lg px-2.5 py-1 font-medium text-gray-700 dark:text-gray-200 hover:text-rose-700 dark:hover:text-rose-300 hover:underline disabled:opacity-40"
          >
            {post.is_hidden ? 'Unhide' : 'Hide'}
          </button>
        )}
      </div>
    </article>
  );
}

export default function MadrichCohortFeed() {
  const { orgSlug, user } = useAuth();
  const [feed, setFeed] = useState(null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState(null);
  const backTo = backHomePath(user);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [feedData, memberData] = await Promise.all([
        fetchCohortFeed(orgSlug),
        fetchCohortMembers(orgSlug).catch(() => ({ results: [] })),
      ]);
      setFeed(feedData);
      setMembers(memberData?.results || []);
    } catch {
      setError('Could not load the cohort feed.');
    }
  }, [orgSlug]);

  useEffect(() => { load(); }, [load]);

  const handleLike = useCallback(async (shareId) => {
    await toggleShareLike(orgSlug, shareId);
    await load();
  }, [orgSlug, load]);

  const handleHide = useCallback(async (shareId, hidden) => {
    await setShareHidden(orgSlug, shareId, hidden);
    await load();
  }, [orgSlug, load]);

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-cohort-error">
        <BackLink to={backTo} label="Back to home" className="mb-2" data-testid="md-cohort-back" />
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={load} className="mt-3 text-sm text-indigo-700 dark:text-indigo-300 underline">
          Retry
        </button>
      </div>
    );
  }

  const posts = feed?.results || [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <div>
        <BackLink to={backTo} label="Back to home" data-testid="md-cohort-back" />
        <div className="mt-2 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-4 shadow-md">
          <h1 className="text-xl font-bold text-white">My cohort</h1>
          <p className="text-sm text-violet-50">
            Ideas your classmates chose to share from their reflections.
          </p>
        </div>
      </div>

      <MembersCard members={members} />

      {!feed ? (
        <CardSkeleton rows={4} data-testid="md-cohort-loading" />
      ) : posts.length === 0 ? (
        <EmptyState title="No posts yet" data-testid="md-cohort-empty">
          When someone shares an idea with the cohort, it shows up here.
        </EmptyState>
      ) : (
        <div className="space-y-3" data-testid="md-cohort-list">
          {posts.map((post) => (
            <Post key={post.id} post={post} onLike={handleLike} onHide={handleHide} />
          ))}
        </div>
      )}
    </div>
  );
}
