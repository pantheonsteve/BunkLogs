import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';

vi.mock('../../partials/Sidebar', () => ({
  default: () => <aside data-testid="mock-sidebar" />,
}));
vi.mock('../../partials/Header', () => ({
  default: () => <header data-testid="mock-header" />,
}));

import AppLayout from '../AppLayout';

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/tasks" element={<p data-testid="child-content">tasks child</p>} />
          <Route path="/reflect" element={<p data-testid="child-content">reflect child</p>} />
          <Route
            path="/groups/performance"
            element={<p data-testid="child-content">performance child</p>}
          />
          <Route
            path="/supervisor/coverage"
            element={<Navigate to="/groups/performance" replace />}
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('AppLayout (3.32 follow-up: chrome for app routes)', () => {
  it('renders Sidebar + Header + /tasks child via Outlet', () => {
    renderAt('/tasks');
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-header')).toBeInTheDocument();
    expect(screen.getByTestId('child-content')).toHaveTextContent('tasks child');
  });

  it('keeps chrome in place on /reflect', () => {
    renderAt('/reflect');
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-header')).toBeInTheDocument();
    expect(screen.getByTestId('child-content')).toHaveTextContent('reflect child');
  });

  it('keeps chrome in place on /groups/performance', () => {
    renderAt('/groups/performance');
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-header')).toBeInTheDocument();
    expect(screen.getByTestId('child-content')).toHaveTextContent('performance child');
  });

  it('exposes the scroll container so children can rely on it', () => {
    renderAt('/tasks');
    expect(screen.getByTestId('app-layout-scroll')).toBeInTheDocument();
  });
});
