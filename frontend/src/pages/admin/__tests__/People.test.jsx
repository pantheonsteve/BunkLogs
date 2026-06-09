import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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
    listAdminPrograms: vi.fn(),
    previewAdminPeopleDedupe: vi.fn(),
    commitAdminPeopleDedupe: vi.fn(),
  };
});

vi.mock('../../../components/admin/DedupePeopleModal', () => ({
  default: ({ onClose, onCompleted }) => (
    <div data-testid="dedupe-people-modal">
      <button type="button" data-testid="dedupe-modal-close" onClick={onClose}>Close</button>
      <button
        type="button"
        data-testid="dedupe-modal-complete"
        onClick={() => onCompleted({ winner_id: 1 })}
      >
        Complete
      </button>
    </div>
  ),
}));

import {
  listAdminPeople,
  getAdminPerson,
  createAdminPerson,
  listAdminPrograms,
  previewAdminPeopleDedupe,
} from '../../../api/admin';
import AdminPeople from '../People';

const PEOPLE = [
  { id: 1, full_name: 'Alice Admin', email: 'a@example.com' },
  { id: 2, full_name: 'Bob Counselor', email: 'b@example.com' },
];

const PROGRAMS = [
  { id: 10, name: 'Summer 2026' },
];

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
    { id: 100, role: 'counselor', program_name: 'Summer 2026', tags: ['veteran'], is_active: true },
  ],
  recent_activity: [],
};

const BOB_DETAIL = {
  id: 2,
  full_name: 'Bob Counselor',
  email: 'b@example.com',
  first_name: 'Bob',
  last_name: 'Counselor',
  preferred_name: '',
  preferred_language: 'en',
  has_user: false,
  external_ids: {},
  memberships: [],
  recent_activity: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPeople.mockResolvedValue({ results: PEOPLE, count: 2, offset: 0, page_size: 50 });
  listAdminPrograms.mockResolvedValue({ results: PROGRAMS });
  getAdminPerson.mockImplementation(async (id) => (
    id === 1 ? ALICE_DETAIL : BOB_DETAIL
  ));
  previewAdminPeopleDedupe.mockResolvedValue({ ok: true, plans: [] });
});

function renderPeople() {
  return render(
    <MemoryRouter>
      <AdminPeople />
    </MemoryRouter>,
  );
}

describe('AdminPeople (7_13 PR2)', () => {
  it('renders the list and opens the profile drawer for the selected Person', async () => {
    renderPeople();
    expect(await screen.findByTestId('person-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('person-row-2')).toBeInTheDocument();

    expect(screen.getByRole('link', { name: 'Alice Admin' })).toHaveAttribute('href', '/profile/1');
    expect(screen.getByRole('link', { name: 'Bob Counselor' })).toHaveAttribute('href', '/profile/2');

    fireEvent.click(screen.getByTestId('person-row-1'));
    await waitFor(() => expect(getAdminPerson).toHaveBeenCalledWith(1));
    const drawer = await screen.findByTestId('person-drawer');
    expect(drawer.querySelector('h2 a')).toHaveAttribute('href', '/profile/1');
    expect(screen.getByTestId('identity-tab')).toBeInTheDocument();
  });

  it('stacks multiple selected profiles in the drawer', async () => {
    renderPeople();
    await screen.findByTestId('person-row-1');

    fireEvent.click(screen.getByTestId('person-select-1'));
    fireEvent.click(screen.getByTestId('person-select-2'));

    await waitFor(() => {
      expect(screen.getByTestId('person-profile-panel-1')).toBeInTheDocument();
      expect(screen.getByTestId('person-profile-panel-2')).toBeInTheDocument();
    });
    expect(screen.getByTestId('people-selection-toolbar')).toHaveTextContent('2 selected');
  });

  it('opens the dedupe modal when Dedupe is clicked', async () => {
    renderPeople();
    await screen.findByTestId('person-row-1');
    fireEvent.click(screen.getByTestId('person-select-1'));
    fireEvent.click(screen.getByTestId('person-select-2'));
    await screen.findByTestId('people-selection-toolbar');

    fireEvent.click(screen.getByTestId('open-dedupe'));
    expect(await screen.findByTestId('dedupe-people-modal')).toBeInTheDocument();
  });

  it('surfaces the email-conflict response from POST /admin/people/', async () => {
    createAdminPerson.mockRejectedValueOnce({
      response: {
        status: 409,
        data: {
          detail: 'email exists',
          existing_person: { id: 99, full_name: 'Duplicate' },
        },
      },
    });
    renderPeople();
    await screen.findByTestId('person-row-1');
    fireEvent.click(screen.getByTestId('open-add-person'));
    expect(await screen.findByTestId('add-person-modal')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('add-person-save'));

    expect(await screen.findByTestId('add-person-conflict')).toBeInTheDocument();
  });

  it('paginates the people list and passes filter params to the API', async () => {
    listAdminPeople.mockImplementation(async (params = {}) => {
      if (params.last_name_initial === 'B') {
        return {
          results: [PEOPLE[1]],
          count: 1,
          offset: 0,
          page_size: params.page_size ?? 50,
        };
      }
      if ((params.offset ?? 0) >= 50) {
        return {
          results: [PEOPLE[1]],
          count: 75,
          offset: params.offset,
          page_size: params.page_size ?? 50,
        };
      }
      return {
        results: [PEOPLE[0]],
        count: 75,
        offset: params.offset ?? 0,
        page_size: params.page_size ?? 50,
      };
    });

    renderPeople();
    await screen.findByTestId('people-list-pagination');
    expect(screen.getByTestId('people-list-pagination')).toHaveTextContent('Showing 1 to 1 of 75');
    expect(screen.getByTestId('people-page-next')).not.toBeDisabled();

    fireEvent.change(screen.getByTestId('last-name-initial-filter'), { target: { value: 'B' } });
    await waitFor(() => {
      expect(listAdminPeople).toHaveBeenLastCalledWith(
        expect.objectContaining({
          last_name_initial: 'B',
          offset: 0,
        }),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
    expect(await screen.findByTestId('people-list-pagination')).toHaveTextContent('Showing 1 to 1 of 1');

    fireEvent.change(screen.getByTestId('last-name-initial-filter'), { target: { value: '' } });
    await screen.findByTestId('people-page-next');
    fireEvent.click(screen.getByTestId('people-page-next'));
    await waitFor(() => {
      expect(listAdminPeople).toHaveBeenLastCalledWith(
        expect.objectContaining({
          offset: 50,
          page_size: 50,
        }),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
    expect(await screen.findByTestId('person-row-2')).toBeInTheDocument();
    expect(screen.getByTestId('people-list-pagination')).toHaveTextContent('Showing 51 to 51 of 75');
  });
});
