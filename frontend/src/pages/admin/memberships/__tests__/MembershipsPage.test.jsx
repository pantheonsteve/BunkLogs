import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../api', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../../../../api/admin', async () => {
  const actual = await vi.importActual('../../../../api/admin');
  return {
    ...actual,
    listAdminPrograms: vi.fn(),
    listAdminPeople: vi.fn(),
    getAdminPerson: vi.fn(),
    inviteAdminPerson: vi.fn(),
  };
});

vi.mock('../../../../components/admin/DeletePersonModal', () => ({
  default: () => null,
}));

import api from '../../../../api';
import {
  listAdminPrograms,
  listAdminPeople,
  getAdminPerson,
} from '../../../../api/admin';
import MembershipManagementPage from '../../../MembershipManagementPage';

const activeProgram = {
  id: 1,
  name: 'Summer 2026',
  slug: 'summer-2026',
  is_active: true,
  start_date: '2026-06-01',
};
const endedProgram = {
  id: 2,
  name: 'Summer 2025',
  slug: 'summer-2025',
  is_active: false,
  start_date: '2025-06-01',
};

const ALICE = { id: 10, full_name: 'Alice Admin', email: 'a@example.com' };
const ALICE_DETAIL = {
  ...ALICE,
  first_name: 'Alice',
  last_name: 'Admin',
  preferred_name: '',
  preferred_language: 'en',
  memberships: [],
  recent_activity: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPrograms.mockImplementation(async (status) => {
    if (status === 'active') {
      return { results: [activeProgram] };
    }
    return { results: [activeProgram, endedProgram] };
  });
  listAdminPeople.mockResolvedValue({ results: [ALICE], count: 1 });
  getAdminPerson.mockResolvedValue(ALICE_DETAIL);
  api.get.mockResolvedValue({ data: { results: [] } });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <MembershipManagementPage />
    </MemoryRouter>,
  );
}

describe('MembershipManagementPage', () => {
  it('defaults to program roster tab', async () => {
    renderPage();
    expect(await screen.findByTestId('membership-roster-tab')).toBeInTheDocument();
    expect(screen.getByTestId('membership-sub-tab-roster')).toHaveClass('bg-indigo-600');
  });

  it('filters programs by active and ended', async () => {
    renderPage();
    await screen.findByTestId('membership-program-list');

    expect(screen.getByText('Summer 2026')).toBeInTheDocument();
    expect(screen.queryByText('Summer 2025')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('membership-program-filter-ended'));
    expect(screen.getByText('Summer 2025')).toBeInTheDocument();
    expect(screen.queryByText('Summer 2026')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('membership-program-filter-all'));
    expect(screen.getByText('Summer 2026')).toBeInTheDocument();
    expect(screen.getByText('Summer 2025')).toBeInTheDocument();
  });

  it('loads enrolled people when a program is selected', async () => {
    renderPage();
    await screen.findByTestId('membership-program-1');

    fireEvent.click(screen.getByTestId('membership-program-1'));

    await waitFor(() => {
      expect(listAdminPeople).toHaveBeenCalledWith(
        expect.objectContaining({ program: '1' }),
        expect.any(Object),
      );
    });
    expect(await screen.findByTestId('membership-roster-person-10')).toBeInTheDocument();
  });

  it('shows person profile panel when a roster person is selected', async () => {
    renderPage();
    await screen.findByTestId('membership-program-1');
    fireEvent.click(screen.getByTestId('membership-program-1'));
    await screen.findByTestId('membership-roster-person-10');

    fireEvent.click(screen.getByTestId('membership-roster-person-10'));

    await waitFor(() => {
      expect(getAdminPerson).toHaveBeenCalledWith(10);
    });
    expect(await screen.findByTestId('person-profile-panel-10')).toBeInTheDocument();
    expect(screen.getByTestId('people-tab-identity')).toBeInTheDocument();
    expect(screen.getByTestId('people-tab-memberships')).toBeInTheDocument();
    expect(screen.getByTestId('people-tab-activity')).toBeInTheDocument();
  });

  it('switches to tags tab and renders membership table', async () => {
    renderPage();
    await screen.findByTestId('membership-roster-tab');

    fireEvent.click(screen.getByTestId('membership-sub-tab-tags'));

    expect(await screen.findByTestId('membership-tags-tab')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/memberships/'),
      );
    });
    expect(screen.getByTestId('membership-tags-table')).toBeInTheDocument();
  });
});
