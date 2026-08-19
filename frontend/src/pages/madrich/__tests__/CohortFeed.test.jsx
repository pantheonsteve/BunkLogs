/**
 * Cohort feed — Step 4_9 §4.5.
 *
 * Two rules the UI has to hold: you cannot like your own post, and a hidden
 * post is visibly hidden to whoever can still see it rather than silently
 * vanishing.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MadrichCohortFeed from '../CohortFeed';

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => 'tbe',
}));

const userWith = (capability, roles) => ({
  id: 42,
  organizations: [{ slug: 'tbe', name: 'TBE', capability, roles }],
  membership_roles: roles,
});

const post = (id, overrides = {}) => ({
  id,
  author: { id: id * 10, display_name: `Author ${id}` },
  is_mine: false,
  body: `Idea number ${id}`,
  field_key: 'shared_idea',
  created_at: '2026-09-14T12:00:00Z',
  like_count: 1,
  liked_by_me: false,
  can_like: true,
  comment_count: 0,
  thread_id: id + 500,
  unread: false,
  is_hidden: false,
  can_hide: false,
  ...overrides,
});

const feed = {
  count: 3,
  next: null,
  previous: null,
  results: [
    post(1),
    post(2, { is_mine: true, can_like: false, author: { id: 42, display_name: 'Me' } }),
    post(3, { is_hidden: true, can_hide: true }),
  ],
};

// Matches CohortMembersView: `results`, and `id` rather than `person_id`.
const members = {
  results: [
    { id: 10, display_name: 'Author 1', grade_level: 9, initials: 'A1', is_me: false },
  ],
};

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  mockUseAuth.mockReset();
  mockUseAuth.mockReturnValue({
    orgSlug: 'tbe',
    user: userWith('participant', ['madrich']),
  });
  postMock.mockResolvedValue({ data: {} });
  getMock.mockImplementation((url) => Promise.resolve({
    data: url.includes('/cohort/members/') ? members : feed,
  }));
});

function renderFeed() {
  return render(<MemoryRouter><MadrichCohortFeed /></MemoryRouter>);
}

describe('Cohort feed', () => {
  it('lists posts with their like counts and comment links', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-post-1'));
    expect(screen.getByTestId('cohort-post-1')).toHaveTextContent('Idea number 1');
    expect(screen.getByTestId('cohort-like-1')).toHaveTextContent('1');
    expect(screen.getByTestId('cohort-comments-1')).toHaveAttribute(
      'href', '/madrich/threads/501',
    );
  });

  it('will not let you like your own post', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-like-2'));
    expect(screen.getByTestId('cohort-like-2')).toBeDisabled();
  });

  it('toggles a like through the react endpoint', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-like-1'));
    await userEvent.click(screen.getByTestId('cohort-like-1'));
    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/cohort/shares/1/react/',
      {},
      expect.objectContaining({ headers: { 'X-Organization-Slug': 'tbe' } }),
    );
  });

  it('marks a hidden post as hidden and offers to unhide it', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-post-3'));
    expect(screen.getByTestId('cohort-hidden-3')).toHaveTextContent('Hidden from the cohort');
    expect(screen.getByTestId('cohort-hide-3')).toHaveTextContent('Unhide');

    await userEvent.click(screen.getByTestId('cohort-hide-3'));
    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/cohort/shares/3/hide/',
      { hidden: false },
      expect.objectContaining({ headers: { 'X-Organization-Slug': 'tbe' } }),
    );
  });

  it('offers no moderation control to someone without the permission', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-post-1'));
    expect(screen.queryByTestId('cohort-hide-1')).toBeNull();
  });

  it('lists cohort members with initials', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('md-cohort-members'));
    expect(screen.getByTestId('md-cohort-members')).toHaveTextContent('A1');
    expect(screen.getByTestId('md-cohort-members')).toHaveTextContent('Author 1');
  });

  it('sends a Madrich home to their dashboard and an admin to Admin Home', async () => {
    renderFeed();
    await waitFor(() => screen.getByTestId('md-cohort-back'));
    expect(screen.getByTestId('md-cohort-back')).toHaveAttribute('href', '/madrich');

    mockUseAuth.mockReturnValue({
      orgSlug: 'tbe',
      user: userWith('admin', ['admin']),
    });
    renderFeed();
    await waitFor(() => {
      const links = screen.getAllByTestId('md-cohort-back');
      expect(links[links.length - 1]).toHaveAttribute('href', '/admin/home');
    });
  });

  it('renders a Quill-authored body as formatted text, not raw tags', async () => {
    getMock.mockImplementation((url) => Promise.resolve({
      data: url.includes('/cohort/members/')
        ? members
        : { ...feed, results: [post(1, { body: '<p>I had this really great idea.</p>' })] },
    }));
    renderFeed();
    await waitFor(() => screen.getByTestId('cohort-post-1'));
    const article = screen.getByTestId('cohort-post-1');
    expect(article).toHaveTextContent('I had this really great idea.');
    expect(article.textContent).not.toContain('<p>');
    expect(article.querySelector('p')).not.toBeNull();
  });

  it('shows an empty state when nobody has shared yet', async () => {
    getMock.mockImplementation((url) => Promise.resolve({
      data: url.includes('/cohort/members/') ? members : { ...feed, count: 0, results: [] },
    }));
    renderFeed();
    await waitFor(() => screen.getByTestId('md-cohort-empty'));
  });
});
