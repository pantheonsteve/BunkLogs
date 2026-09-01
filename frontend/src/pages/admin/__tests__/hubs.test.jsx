/**
 * The two hub pages the flattened sidebar points at.
 *
 * The thing worth guarding is that each hub lists the destinations that
 * left the nav, and that Reports respects the tenant's surfaces -- a camp
 * must not be offered the religious-school reflection reports.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({ useAuth: () => mockUseAuth() }));

import HubPage from '../HubPage';
import FormsHub from '../forms/FormsHub';
import ReportsHub from '../reports/ReportsHub';

function renderPage(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function orgUser(programTypes) {
  return {
    organizations: [{
      slug: 'org', name: 'Org', capability: 'admin',
      roles: ['admin'], program_types: programTypes,
    }],
    membership_roles: ['admin'],
  };
}

function hrefs() {
  return screen.getAllByRole('link').map((a) => a.getAttribute('href'));
}

beforeEach(() => {
  mockUseAuth.mockReset();
});

describe('FormsHub', () => {
  it('lists templates and form fields', () => {
    renderPage(<FormsHub />);
    expect(hrefs()).toEqual(['/admin/templates', '/admin/field-keys']);
    expect(screen.getByRole('heading', { name: 'Forms' })).toBeInTheDocument();
    expect(screen.getByText('Form fields')).toBeInTheDocument();
  });
});

describe('ReportsHub', () => {
  it('gives a religious school the reflection reports', () => {
    mockUseAuth.mockReturnValue({ user: orgUser(['religious_school']) });
    renderPage(<ReportsHub />);
    expect(hrefs()).toEqual([
      '/admin/reflections',
      '/admin/reflections/growth',
      '/admin/reflections/availability',
    ]);
  });

  it('gives a camp request planning instead', () => {
    mockUseAuth.mockReturnValue({ user: orgUser(['summer_camp']) });
    renderPage(<ReportsHub />);
    expect(hrefs()).toEqual(['/admin/catalog/planning']);
  });

});

describe('HubPage', () => {
  it('says so rather than rendering an empty grid when there is nothing to link', () => {
    renderPage(
      <HubPage title="Reports" links={[]} emptyTitle="Nothing here yet." />,
    );
    expect(screen.queryAllByRole('link')).toHaveLength(0);
    expect(screen.getByText('Nothing here yet.')).toBeInTheDocument();
  });
});
