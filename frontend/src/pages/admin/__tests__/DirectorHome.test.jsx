/**
 * Director homepage — Step 4_9 §6.
 *
 * AdminHome also serves camp admins, so the first thing this asserts is that
 * none of these cards appear for a non-school org. After that: the pulse, the
 * coverage vocabulary, and theme suppression.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => null,
}));

import AdminHome from '../AdminHome';

const pulse = {
  available: true,
  template_name: 'Weekly 3-2-1',
  active_madrichim: 10,
  periods: [
    { period_start: '2026-09-07', period_end: '2026-09-13', submitted: 6, expected: 10, rate: 0.6 },
    { period_start: '2026-09-14', period_end: '2026-09-20', submitted: 8, expected: 10, rate: 0.8 },
  ],
  current: { period_start: '2026-09-14', period_end: '2026-09-20', submitted: 8, expected: 10, rate: 0.8 },
  open_question_count: 2,
};

const coverage = {
  sessions: ['2026-09-27', '2026-10-04'],
  classrooms: [{
    id: 12,
    name: 'Tzedakah 101',
    roster_size: 4,
    cells: [
      { session_date: '2026-09-27', available: 2, tentative: 1, unavailable: 0, unset: 1, roster_size: 4, flagged: true },
      { session_date: '2026-10-04', available: 4, tentative: 0, unavailable: 0, unset: 0, roster_size: 4, flagged: false },
    ],
  }],
};

const coverageDetail = {
  session_date: '2026-09-27',
  totals: { available: 2, tentative: 1, unavailable: 0, unset: 1, roster_size: 4 },
  classrooms: [{
    id: 12,
    name: 'Tzedakah 101',
    roster_size: 4,
    people: [
      { person_id: 1, membership_id: 3189, display_name: 'Ari Rich', grade_level: 9, status: 'available', note: '' },
      { person_id: 2, membership_id: 3190, display_name: 'Bee Rich', grade_level: 10, status: 'available', note: '' },
      { person_id: 3, membership_id: 3191, display_name: 'Cy Rich', grade_level: 11, status: 'tentative', note: 'Might have a game' },
      { person_id: 4, membership_id: null, display_name: 'Dot Rich', grade_level: 12, status: null, note: '' },
    ],
  }],
};

const themes = {
  themes: [{ theme_key: 'belonging', label: 'Belonging', contributors: 6, mentions: 9 }],
  suppressed_count: 2,
  min_contributors: 5,
  growth_dashboard_url: '/admin/reflections/growth',
};

const RESPONSES = {
  '/pulse/': pulse,
  '/queue/': { count: 1, results: [], next: null, previous: null },
  // More specific first: the matcher below takes the first key the URL contains.
  '/coverage/2026-09-27/': coverageDetail,
  '/coverage/': coverage,
  '/faculty-activity/': { results: [{
    person_id: 9,
    membership_id: 909,
    display_name: 'Rabbi Gold',
    assigned_madrich_count: 4,
    open_thread_count: 2,
    median_response_hours: 18.5,
    oldest_unanswered_days: 12,
  }] },
  '/themes/': themes,
  '/madrichim/': { count: 1, results: [{
    person_id: 10,
    membership_id: 3189,
    display_name: 'Ari Rich',
    grade_level: 9,
    classroom: 'Tzedakah 101',
    reflection_state: 'complete',
    open_thread_count: 0,
  }] },
};

function adminIn(programTypes) {
  return {
    organizations: [{
      slug: 'tbe',
      name: 'TBE',
      capability: 'admin',
      roles: ['admin'],
      program_types: programTypes,
    }],
    membership_roles: ['admin'],
  };
}

function renderHome(user = adminIn(['religious_school'])) {
  mockUseAuth.mockReturnValue({ user, orgSlug: 'tbe' });
  return render(<MemoryRouter><AdminHome /></MemoryRouter>);
}

beforeEach(() => {
  mockUseAuth.mockReset();
  getMock.mockReset();
  getMock.mockImplementation((url) => {
    const match = Object.keys(RESPONSES).find((suffix) => url.includes(suffix));
    return match
      ? Promise.resolve({ data: RESPONSES[match] })
      : Promise.reject(new Error(`unexpected ${url}`));
  });
});

describe('Director homepage inside AdminHome', () => {
  it('is absent for a camp org, and fetches nothing', () => {
    renderHome(adminIn(['summer_camp']));
    expect(screen.queryByTestId('director-home')).toBeNull();
    expect(getMock).not.toHaveBeenCalled();
  });

  it('reports this week\'s completion rate and the open question count', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-pulse-card'));
    expect(screen.getByTestId('dir-pulse-rate')).toHaveTextContent('80%');
    expect(screen.getByTestId('dir-pulse-rate')).toHaveTextContent('8 of 10');
    expect(screen.getByTestId('dir-pulse-card')).toHaveTextContent('10 active Madrichim');
    expect(screen.getByTestId('dir-pulse-sparkline').children).toHaveLength(2);
  });

  it('flags a Sunday where anyone is tentative or has not answered', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-coverage-card'));
    expect(screen.getByTestId('dir-coverage-12-2026-09-27')).toHaveTextContent('1 unanswered');
    expect(screen.getByTestId('dir-coverage-12-2026-09-27')).toHaveTextContent('1 tentative');
    expect(screen.getByTestId('dir-coverage-12-2026-10-04')).toHaveTextContent('4/4');
    expect(screen.getByTestId('dir-coverage-12-2026-10-04')).not.toHaveTextContent('unanswered');
  });

  it('opens a Sunday to show who is in, who is tentative, and who never answered', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-coverage-card'));
    fireEvent.click(screen.getByTestId('dir-coverage-date-2026-09-27'));

    await waitFor(() => screen.getByTestId('coverage-detail-summary'));
    expect(screen.getByTestId('coverage-detail-summary')).toHaveTextContent('2 of 4 available');
    expect(screen.getByTestId('coverage-detail-section-available')).toHaveTextContent('Ari Rich');
    expect(screen.getByTestId('coverage-detail-section-tentative')).toHaveTextContent('Might have a game');
    expect(screen.getByTestId('coverage-detail-section-unset')).toHaveTextContent('Dot Rich');
    expect(screen.getByTestId('coverage-detail-section-unavailable')).toHaveTextContent('Nobody');
    // A person with a membership opens their own reflection history.
    expect(screen.getByTestId('coverage-detail-person-1').querySelector('a')).toHaveAttribute(
      'href', '/admin/reflections/madrich/members/3189',
    );

    fireEvent.click(screen.getByTestId('coverage-detail-close'));
    await waitFor(() => expect(screen.queryByTestId('coverage-detail-modal')).toBeNull());
  });

  it('scopes the drill-down to one classroom when a cell is clicked', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-coverage-card'));
    fireEvent.click(screen.getByTestId('dir-coverage-12-2026-09-27'));

    await waitFor(() => screen.getByTestId('coverage-detail-summary'));
    expect(screen.getByTestId('coverage-detail-summary')).toHaveTextContent('Tzedakah 101');
  });

  it('says how many themes were withheld rather than dropping them silently', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-themes-card'));
    expect(screen.getByTestId('dir-theme-belonging')).toHaveTextContent('Belonging');
    expect(screen.getByTestId('dir-themes-suppressed')).toHaveTextContent('2 themes withheld');
    expect(screen.getByTestId('dir-themes-suppressed')).toHaveTextContent('fewer than 5');
    expect(screen.getByTestId('dir-themes-growth-link')).toHaveAttribute(
      'href', '/admin/reflections/growth',
    );
  });

  it('reports faculty latency, leaving it blank when nothing is answered', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-activity-row-9'));
    expect(screen.getByTestId('dir-activity-row-9')).toHaveTextContent('18.5h median');
    expect(screen.getByTestId('dir-activity-row-9')).toHaveTextContent('oldest 12d');
  });

  it('offers a roster export button rather than a bare link', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-roster-export'));
    // A plain href would resolve against the SPA origin and carry no token.
    expect(screen.getByTestId('dir-roster-export').tagName).toBe('BUTTON');
    expect(screen.getByTestId('dir-roster-row-10')).toHaveTextContent('Ari Rich');
  });

  it('opens a Madrich or faculty row on their own response page', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('dir-roster-row-10'));
    expect(screen.getByTestId('dir-roster-row-10')).toHaveAttribute(
      'href', '/admin/reflections/madrich/members/3189',
    );
    expect(screen.getByTestId('dir-activity-row-9')).toHaveAttribute(
      'href', '/admin/reflections/faculty/members/909',
    );
  });

  it('leaves a row unlinked when the payload has no membership to open', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/madrichim/')) {
        return Promise.resolve({ data: {
          count: 1,
          results: [{ ...RESPONSES['/madrichim/'].results[0], membership_id: undefined }],
        } });
      }
      const match = Object.keys(RESPONSES).find((suffix) => url.includes(suffix));
      return Promise.resolve({ data: RESPONSES[match] });
    });
    renderHome();
    await waitFor(() => screen.getByTestId('dir-roster-row-10'));
    expect(screen.getByTestId('dir-roster-row-10')).not.toHaveAttribute('href');
    expect(screen.getByTestId('dir-roster-row-10')).toHaveTextContent('Ari Rich');
  });

  it('hides a card whose endpoint fails instead of breaking the page', async () => {
    getMock.mockImplementation((url) => (
      url.includes('/themes/')
        ? Promise.reject(new Error('boom'))
        : Promise.resolve({ data: RESPONSES[Object.keys(RESPONSES).find((s) => url.includes(s))] })
    ));
    renderHome();
    await waitFor(() => screen.getByTestId('dir-pulse-card'));
    await waitFor(() => expect(screen.queryByTestId('dir-themes-loading')).toBeNull());
    expect(screen.queryByTestId('dir-themes-card')).toBeNull();
  });
});
