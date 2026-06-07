import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../api/admin', () => ({
  listAdminPeople: vi.fn(),
  getAdminPerson: vi.fn(),
  createAdminPerson: vi.fn(),
  patchAdminPerson: vi.fn(),
  addAdminMembership: vi.fn(),
  patchAdminMembership: vi.fn(),
  deactivateAdminMembership: vi.fn(),
  inviteAdminPerson: vi.fn(),
  listAdminPrograms: vi.fn(),
}));

import {
  listAdminPeople,
  getAdminPerson,
  createAdminPerson,
  listAdminPrograms,
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
  memberships: [
    { id: 100, role: 'counselor', program_name: 'Summer 2026', tags: ['veteran'], is_active: true },
  ],
  recent_activity: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPeople.mockResolvedValue({ results: PEOPLE });
  listAdminPrograms.mockResolvedValue({ results: PROGRAMS });
  getAdminPerson.mockResolvedValue(ALICE_DETAIL);
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
});
