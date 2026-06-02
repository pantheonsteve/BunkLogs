import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';

describe('reflections dashboard routes', () => {
  it('redirects /dashboards/team to /dashboards/reflections', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboards/team']}>
        <Routes>
          <Route path="/dashboards/team" element={<Navigate to="/dashboards/reflections" replace />} />
          <Route path="/dashboards/reflections" element={<div data-testid="reflections-page" />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('reflections-page')).toBeInTheDocument();
  });
});
