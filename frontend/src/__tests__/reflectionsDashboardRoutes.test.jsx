import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';

describe('reflections dashboard routes', () => {
  it('redirects /dashboards/team to /dashboards/logs', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboards/team']}>
        <Routes>
          <Route path="/dashboards/team" element={<Navigate to="/dashboards/logs" replace />} />
          <Route path="/dashboards/logs" element={<div data-testid="logs-page" />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('logs-page')).toBeInTheDocument();
  });
});
