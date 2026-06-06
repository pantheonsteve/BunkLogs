import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import HelpArticlePage from '../HelpArticlePage';

function renderAt(slug) {
  return render(
    <MemoryRouter initialEntries={[`/help/${slug}`]}>
      <Routes>
        <Route path="/help/:slug" element={<HelpArticlePage />} />
        <Route path="/help" element={<div>Help home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('HelpArticlePage', () => {
  it('renders a known guide heading', () => {
    renderAt('form-types');
    expect(screen.getByTestId('help-article-form-types')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /form types/i })).toBeInTheDocument();
  });

  it('shows not found for unknown slug', () => {
    renderAt('does-not-exist');
    expect(screen.getByText(/guide not found/i)).toBeInTheDocument();
  });

  it('links internal markdown guides to /help routes', () => {
    renderAt('form-types');
    const related = screen.getByRole('link', { name: /templates & assignments/i });
    expect(related).toHaveAttribute('href', '/help/templates-and-assignments');
  });
});
