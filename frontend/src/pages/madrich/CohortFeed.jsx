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
import {
  fetchCohortFeed, fetchCohortMembers, setShareHidden, toggleShareLike,
} from '../../api/threads';
import { useAuth } from '../../auth/AuthContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import EmptyState from '../../components/ui/EmptyState';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';

function MembersCard({ members }) {
  if (!members || members.length === 0) return null;
  return (
    <HomeCard
      title="My cohort"
      subtitle={`${members.length} classmate${members.length === 1 ? '' : 's'}`}
      data-testid="md-cohort-members"
    >
      <ul className="flex flex-wrap gap-2">
        {members.map((m) => (
          <li
            key={m.id}
            className="inline-flex items-center gap-2 rounded-full border border-gray-200 dark:border-gray-700 pl-1 pr-3 py-1"
          >
            <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
              {m.initials}
            </span>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {m.display_name}
              {typeof m.grade_level === 'number' && (
                <span className="text-gray-500 dark:text-gray-400"> · {m.grade_level}</span>
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
      className={`rounded-xl border bg-white dark:bg-gray-800 p-4 ${
        post.is_hidden
          ? 'border-red-300 dark:border-red-800'
          : 'border-gray-200 dark:border-gray-700'
      }`}
      data-testid={`cohort-post-${post.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-900 dark:text-white">
          {post.author?.display_name}
          {post.is_mine && (
            <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">you</span>
          )}
        </p>
        {post.unread && <UnreadDot label="New activity" />}
      </div>

      {post.is_hidden && (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400" data-testid={`cohort-hidden-${post.id}`}>
          Hidden from the cohort.
        </p>
      )}

      <p className="mt-2 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
        {post.body}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <button
          type="button"
          disabled={!post.can_like || pending}
          onClick={() => act(() => onLike(post.id))}
          data-testid={`cohort-like-${post.id}`}
          title={post.can_like ? undefined : 'You cannot like your own post'}
          className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 border ${
            post.liked_by_me
              ? 'border-violet-300 dark:border-violet-700 text-violet-700 dark:text-violet-300'
              : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400'
          } disabled:opacity-40`}
        >
          <span aria-hidden="true">♥</span>
          <span>{post.like_count}</span>
          <span className="sr-only">
            {post.liked_by_me ? 'Remove like' : 'Like this post'}
          </span>
        </button>

        {post.thread_id && (
          <Link
            to={`/madrich/threads/${post.thread_id}`}
            className="text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid={`cohort-comments-${post.id}`}
          >
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
            className="text-gray-500 dark:text-gray-400 hover:underline disabled:opacity-40"
          >
            {post.is_hidden ? 'Unhide' : 'Hide'}
          </button>
        )}
      </div>
    </article>
  );
}

export default function MadrichCohortFeed() {
  const { orgSlug } = useAuth();
  const [feed, setFeed] = useState(null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState(null);

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
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={load} className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline">
          Retry
        </button>
      </div>
    );
  }

  const posts = feed?.results || [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <div>
        <Link to="/madrich" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← Back to home
        </Link>
        <h1 className="mt-1 text-xl font-bold text-gray-900 dark:text-white">My cohort</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Ideas your classmates chose to share from their reflections.
        </p>
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
