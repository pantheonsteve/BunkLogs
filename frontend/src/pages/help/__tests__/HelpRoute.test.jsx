import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import HelpRoute from '../HelpRoute';

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const orgUser = (capability, roles = []) => ({
  organizations: [{ slug: 'clc', capability, roles }],
});

function renderAt(path, user) {
  mockUseAuth.mockReturnValue({ user, isAuthenticated: !!user, loading: false });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/help"
          element={
            <HelpRoute>
              <div data-testid="help-content">Help</div>
            </HelpRoute>
          }
        />
        <Route path="/" element={<div data-testid="home">Home</div>} />
        <Route path="/signin" element={<div data-testid="signin">Signin</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUseAuth.mockReset();
});

describe('HelpRoute', () => {
  it('allows program leads', () => {
    renderAt('/help', orgUser('program_lead', ['leadership_team']));
    expect(screen.getByTestId('help-content')).toBeInTheDocument();
  });

  it('allows admins', () => {
    renderAt('/help', orgUser('admin', ['admin']));
    expect(screen.getByTestId('help-content')).toBeInTheDocument();
  });

  it('redirects counselors', () => {
    renderAt('/help', orgUser('participant', ['counselor']));
    expect(screen.getByTestId('home')).toBeInTheDocument();
  });
});
