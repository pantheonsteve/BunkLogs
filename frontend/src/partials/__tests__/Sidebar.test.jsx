import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Stub the auth hook so the sidebar receives a Super Admin user.
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { is_staff: true, role: 'Counselor' },
  }),
}));

// Stub the camp logo image import (jpeg) to keep the test fast.
vi.mock('../../../src/images/clc-logo.jpeg', () => ({ default: 'logo.jpg' }));

import Sidebar from '../Sidebar';

function renderSidebar() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Sidebar sidebarOpen={true} setSidebarOpen={() => {}} />
    </MemoryRouter>,
  );
}

describe('Sidebar admin navigation (3.26)', () => {
  it('renames the legacy "Tests" group to "Admin"', () => {
    renderSidebar();
    expect(screen.getByText('Admin')).toBeInTheDocument();
    expect(screen.queryByText('Tests')).not.toBeInTheDocument();
  });

  it('renders Admin group items (home, Memberships, Templates, Groups)', () => {
    renderSidebar();
    // Member is link text, scope to anchors so we don't catch page headings.
    const adminLinks = screen.getAllByRole('link').map((a) => a.getAttribute('href'));
    expect(adminLinks).toEqual(expect.arrayContaining([
      '/admin',
      '/admin/memberships',
      '/admin/templates',
      '/admin/groups',
    ]));
  });

  it('renders the Dashboards group with canonical /dashboards/* targets', () => {
    renderSidebar();
    expect(screen.getByText('Dashboards')).toBeInTheDocument();
    const links = screen.getAllByRole('link').map((a) => a.getAttribute('href'));
    expect(links).toEqual(expect.arrayContaining([
      '/dashboards',
      '/dashboards/coverage',
      '/dashboards/authors',
      '/dashboards/concerns',
      '/dashboards/team',
      '/dashboards/wellness',
    ]));
    // Legacy off-pattern URLs must NOT appear in the sidebar.
    expect(links).not.toContain('/team/dashboard');
    expect(links).not.toContain('/wellness/dashboard');
  });

  it('renders "My tasks" as a top-level entry', () => {
    renderSidebar();
    expect(screen.getByText('My tasks')).toBeInTheDocument();
  });
});

describe('Sidebar wayfinding (3.27)', () => {
  it('renames the Counselor role entry from "My Reflections" to "Counselor home"', () => {
    renderSidebar();
    // Counselor role link now reads "Counselor home" and is the only entry
    // pointing at the legacy /counselor-dashboard.
    expect(screen.getByText('Counselor home')).toBeInTheDocument();
    expect(screen.queryByText('My Reflections')).not.toBeInTheDocument();
    const links = screen.getAllByRole('link').map((a) => a.getAttribute('href'));
    expect(links).toContain('/counselor-dashboard');
  });

  it('exposes "My reflections" as a top-level entry pointing at /my-reflections', () => {
    renderSidebar();
    expect(screen.getByText('My reflections')).toBeInTheDocument();
    const links = screen.getAllByRole('link').map((a) => a.getAttribute('href'));
    expect(links).toContain('/my-reflections');
  });
});
