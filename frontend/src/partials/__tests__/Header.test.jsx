import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockUseAuth = vi.fn();
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));
const mockUseAdminProgram = vi.fn();
vi.mock('../../context/AdminProgramContext', () => ({
  useAdminProgram: () => mockUseAdminProgram(),
}));
vi.mock('../../components/ThemeToggle', () => ({ default: () => null }));
vi.mock('../../api/admin', () => ({ searchAdmin: vi.fn() }));

import Header, { programDayLabel } from '../Header';

const SUMMER = {
  id: 7,
  name: 'Crane Lake Camp Summer 2027 Session 1',
  display_alias: 'Summer 2027 · Session 1',
  start_date: '2027-07-02',
  end_date: '2027-07-27',
  is_active: true,
};

function adminUser() {
  return {
    first_name: 'Dana',
    last_name: 'Shapiro',
    organizations: [{ slug: 'clc', capability: 'admin', roles: ['admin'], program_types: ['summer_camp'] }],
    membership_roles: ['admin'],
  };
}

function renderHeader({ user = adminUser(), program = SUMMER } = {}) {
  mockUseAuth.mockReturnValue({ user, userProfile: user, logout: vi.fn() });
  mockUseAdminProgram.mockReturnValue({
    programs: program ? [program] : [],
    programId: program ? String(program.id) : '',
    program,
    ready: true,
    setProgramId: vi.fn(),
  });
  return render(
    <MemoryRouter>
      <Header sidebarOpen={false} setSidebarOpen={() => {}} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUseAuth.mockReset();
  mockUseAdminProgram.mockReset();
});

describe('Header (8_3)', () => {
  it('shows the program, search, and the account avatar for an admin', () => {
    renderHeader();
    expect(screen.getByTestId('admin-program-switcher')).toHaveTextContent('Summer 2027 · Session 1');
    expect(screen.getByLabelText('Admin global search')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Account menu for Dana Shapiro' })).toHaveTextContent('DS');
  });

  it('hides search and the program pill for a counselor outside the admin program scope', () => {
    renderHeader({
      user: {
        first_name: 'Sam',
        organizations: [{ slug: 'clc', capability: 'participant', roles: ['counselor'], program_types: ['summer_camp'] }],
        membership_roles: ['counselor'],
      },
      program: null,
    });
    expect(screen.queryByLabelText('Admin global search')).not.toBeInTheDocument();
    expect(screen.queryByTestId('admin-program-switcher')).not.toBeInTheDocument();
    expect(screen.getByTestId('header-today')).toBeInTheDocument();
  });

  it('counts program days inclusively and only inside the program', () => {
    expect(programDayLabel(SUMMER, new Date(2027, 6, 13))).toBe('Day 12 of 26');
    expect(programDayLabel(SUMMER, new Date(2027, 6, 2))).toBe('Day 1 of 26');
    expect(programDayLabel(SUMMER, new Date(2027, 7, 1))).toBeNull();
    expect(programDayLabel({ start_date: null }, new Date())).toBeNull();
  });
});
