/**
 * People after it absorbed Memberships.
 *
 * The list now carries the facts the filters narrow on, row-click and
 * checkbox are different gestures, and merge is a guarded bulk action.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../api/admin', async () => {
  const actual = await vi.importActual('../../../api/admin');
  return {
    ...actual,
    listAdminPeople: vi.fn(),
    getAdminPerson: vi.fn(),
    createAdminPerson: vi.fn(),
    patchAdminPerson: vi.fn(),
    addAdminMembership: vi.fn(),
    patchAdminMembership: vi.fn(),
    deactivateAdminMembership: vi.fn(),
    inviteAdminPerson: vi.fn(),
    bulkInviteAdminPeople: vi.fn(),
    listAdminPrograms: vi.fn(),
    previewAdminPeopleDedupe: vi.fn(),
    commitAdminPeopleDedupe: vi.fn(),
    getAdminSupervisorStatus: vi.fn(),
    listAdminAssignments: vi.fn(),
  };
});

vi.mock('../../../components/admin/DedupePeopleModal', () => ({
  default: ({ onClose }) => (
    <div data-testid="dedupe-people-modal">
      <button type="button" onClick={onClose}>Close</button>
    </div>
  ),
}));

vi.mock('../../../components/admin/DeletePersonModal', () => ({
  default: ({ person, onCompleted }) => (
    <div data-testid="delete-person-modal">
      <span>{person.full_name}</span>
      <button type="button" onClick={() => onCompleted({ person_id: person.id })}>
        Complete
      </button>
    </div>
  ),
}));

import {
  listAdminPeople,
  getAdminPerson,
  createAdminPerson,
  bulkInviteAdminPeople,
  listAdminPrograms,
  getAdminSupervisorStatus,
  listAdminAssignments,
} from '../../../api/admin';
import AdminPeople from '../People';

const PEOPLE = [
  {
    id: 1,
    full_name: 'Alice Admin',
    email: 'a@example.com',
    roles: ['counselor'],
    groups: ['Bunk Maple'],
    invite_status: 'active',
    last_login: new Date().toISOString(),
  },
  {
    id: 2,
    full_name: 'Bob Counselor',
    email: 'b@example.com',
    roles: [],
    groups: [],
    invite_status: 'never',
    last_login: null,
  },
];

const PROGRAMS = [{ id: 10, name: 'Summer 2026' }];

const ALICE_DETAIL = {
  id: 1,
  full_name: 'Alice Admin',
  email: 'a@example.com',
  first_name: 'Alice',
  last_name: 'Admin',
  preferred_name: '',
  preferred_language: 'en',
  has_user: true,
  external_ids: { campminder_id: '111' },
  memberships: [
    { id: 100, role: 'counselor', program_id: 10, program_name: 'Summer 2026', tags: ['veteran'], is_active: true },
  ],
  recent_activity: [],
};

const BOB_DETAIL = {
  ...ALICE_DETAIL,
  id: 2,
  full_name: 'Bob Counselor',
  first_name: 'Bob',
  last_name: 'Counselor',
  email: 'b@example.com',
  has_user: false,
  external_ids: {},
  memberships: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPeople.mockResolvedValue({ results: PEOPLE, count: 2, offset: 0, page_size: 50 });
  listAdminPrograms.mockResolvedValue({ results: PROGRAMS });
  getAdminPerson.mockImplementation(async (id) => (id === 1 ? ALICE_DETAIL : BOB_DETAIL));
  getAdminSupervisorStatus.mockResolvedValue({
    is_supervisor: false,
    can_view_reflections: false,
    supervised_entities: {},
    supervised_people: { count: 0, people: [] },
  });
  listAdminAssignments.mockResolvedValue({ results: [] });
  bulkInviteAdminPeople.mockResolvedValue({
    sent_count: 1,
    skipped_count: 1,
    sent: [{ person_id: 1, name: 'Alice Admin' }],
    skipped: [{ person_id: 2, name: 'Bob Counselor', reason: 'Person has no email.' }],
  });
});

function renderPeople(entry = '/admin/people') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <AdminPeople />
    </MemoryRouter>,
  );
}

describe('AdminPeople', () => {
  it('shows role, groups and invite status in the row', async () => {
    renderPeople();
    const alice = await screen.findByTestId('person-row-1');
    expect(within(alice).getByText('counselor')).toBeInTheDocument();
    expect(within(alice).getByText('Bunk Maple')).toBeInTheDocument();
    expect(within(alice).getByText('Signed in')).toBeInTheDocument();
    expect(within(screen.getByTestId('person-row-2')).getByText('Not invited')).toBeInTheDocument();
  });

  it('previews on row click and selects on checkbox, without conflating the two', async () => {
    renderPeople();
    const alice = await screen.findByTestId('person-row-1');

    fireEvent.click(within(alice).getByRole('checkbox'));
    expect(await screen.findByTestId('bulk-action-bar')).toHaveTextContent('1 selected');
    expect(screen.queryByTestId('person-profile-panel-1')).toBeNull();

    fireEvent.click(within(alice).getByText('Alice Admin').closest('td'));
    expect(await screen.findByTestId('person-profile-panel-1')).toBeInTheDocument();
  });

  it('reads ?invite_status= from the URL so the dashboard can link to the fix', async () => {
    renderPeople('/admin/people?invite_status=never');
    await waitFor(() => {
      expect(listAdminPeople).toHaveBeenLastCalledWith(
        expect.objectContaining({ invite_status: 'never' }),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
    expect(screen.getByTestId('people-invite-filter-never')).toHaveAttribute('aria-pressed', 'true');
  });

  it('reports who was skipped after a bulk invite rather than claiming success', async () => {
    renderPeople();
    const alice = await screen.findByTestId('person-row-1');
    fireEvent.click(within(alice).getByRole('checkbox'));
    fireEvent.click(within(await screen.findByTestId('person-row-2')).getByRole('checkbox'));

    fireEvent.click(await screen.findByTestId('bulk-invite'));
    await waitFor(() => expect(bulkInviteAdminPeople).toHaveBeenCalledWith([1, 2]));

    const result = await screen.findByTestId('bulk-invite-result');
    expect(result).toHaveTextContent('1 invitation sent');
    expect(result).toHaveTextContent('Bob Counselor — Person has no email.');
  });

  it('will not merge until at least two people are selected', async () => {
    renderPeople();
    const alice = await screen.findByTestId('person-row-1');
    fireEvent.click(within(alice).getByRole('checkbox'));

    fireEvent.click(await screen.findByTestId('people-bulk-overflow'));
    expect(screen.getByTestId('open-dedupe')).toBeDisabled();
    fireEvent.keyDown(document, { key: 'Escape' });

    fireEvent.click(within(screen.getByTestId('person-row-2')).getByRole('checkbox'));
    fireEvent.click(screen.getByTestId('people-bulk-overflow'));
    fireEvent.click(screen.getByTestId('open-dedupe'));
    expect(await screen.findByTestId('dedupe-people-modal')).toBeInTheDocument();
  });

  it('offers the existing record when the email is already taken', async () => {
    createAdminPerson.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: 'email exists', existing_person: { id: 99, full_name: 'Duplicate' } },
      },
    });
    renderPeople();
    await screen.findByTestId('person-row-1');
    fireEvent.click(screen.getByTestId('open-add-person'));
    fireEvent.click(await screen.findByTestId('add-person-save'));
    expect(await screen.findByTestId('add-person-conflict')).toBeInTheDocument();
  });

  it('keeps delete behind the profile overflow menu', async () => {
    renderPeople();
    const alice = await screen.findByTestId('person-row-1');
    fireEvent.click(within(alice).getByText('Alice Admin').closest('td'));
    await screen.findByTestId('person-profile-panel-1');

    expect(screen.queryByTestId('delete-person-1')).toBeNull();
    fireEvent.click(screen.getByTestId('person-actions-1'));
    fireEvent.click(screen.getByTestId('delete-person-1'));
    expect(await screen.findByTestId('delete-person-modal')).toBeInTheDocument();
  });

  it('paginates and passes the filter params through', async () => {
    listAdminPeople.mockImplementation(async (params = {}) => (
      (params.offset ?? 0) >= 50
        ? { results: [PEOPLE[1]], count: 75, offset: params.offset, page_size: 50 }
        : { results: [PEOPLE[0]], count: 75, offset: 0, page_size: 50 }
    ));

    renderPeople();
    await screen.findByTestId('people-list-pagination');
    expect(screen.getByTestId('people-list-pagination')).toHaveTextContent('Showing 1 to 1 of 75');

    fireEvent.click(screen.getByTestId('people-page-next'));
    await waitFor(() => {
      expect(listAdminPeople).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 50, page_size: 50 }),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
    expect(await screen.findByTestId('person-row-2')).toBeInTheDocument();
  });
});
