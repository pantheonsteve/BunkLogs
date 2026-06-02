import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../../../partials/Header', () => ({ default: () => null }));
vi.mock('../../../partials/Sidebar', () => ({ default: () => null }));

import DashboardsHub from '../DashboardsHub';

function renderHub() {
  return render(
    <MemoryRouter initialEntries={['/dashboards']}>
      <Routes>
        <Route path="/dashboards" element={<DashboardsHub />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('DashboardsHub', () => {
  it('renders the six dashboard cards plus the subjects helper card', () => {
    renderHub();
    expect(screen.getByTestId('dashboards-hub-card-coverage')).toBeInTheDocument();
    expect(screen.getByTestId('dashboards-hub-card-authors')).toBeInTheDocument();
    expect(screen.getByTestId('dashboards-hub-card-concerns')).toBeInTheDocument();
    expect(screen.getByTestId('dashboards-hub-card-reflections')).toBeInTheDocument();
    expect(screen.getByTestId('dashboards-hub-card-wellness')).toBeInTheDocument();
    expect(screen.getByTestId('dashboards-hub-card-subjects')).toBeInTheDocument();
  });

  it('cards link to canonical /dashboards/* URLs (and subjects goes via /admin/groups)', () => {
    renderHub();
    expect(screen.getByTestId('dashboards-hub-card-coverage')).toHaveAttribute('href', '/dashboards/coverage');
    expect(screen.getByTestId('dashboards-hub-card-authors')).toHaveAttribute('href', '/dashboards/authors');
    expect(screen.getByTestId('dashboards-hub-card-concerns')).toHaveAttribute('href', '/dashboards/concerns');
    expect(screen.getByTestId('dashboards-hub-card-reflections')).toHaveAttribute('href', '/dashboards/reflections');
    expect(screen.getByTestId('dashboards-hub-card-wellness')).toHaveAttribute('href', '/dashboards/wellness');
    expect(screen.getByTestId('dashboards-hub-card-subjects')).toHaveAttribute('href', '/admin/groups');
  });
});
