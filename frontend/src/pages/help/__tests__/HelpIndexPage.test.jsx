import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import HelpIndexPage from '../HelpIndexPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <HelpIndexPage />
    </MemoryRouter>,
  );
}

describe('HelpIndexPage', () => {
  it('lists all help guides', () => {
    renderPage();
    expect(screen.getByTestId('help-card-logs-reflections-observations')).toBeInTheDocument();
    expect(screen.getByTestId('help-card-form-types')).toBeInTheDocument();
    expect(screen.getByTestId('help-card-templates-and-assignments')).toBeInTheDocument();
    expect(screen.getByTestId('help-card-viewing-responses')).toBeInTheDocument();
    expect(screen.getByTestId('help-card-concern-inbox')).toBeInTheDocument();
  });

  it('filters guides by search query', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByTestId('help-search'), 'subject mode');
    expect(screen.getByTestId('help-card-form-types')).toBeInTheDocument();
    expect(screen.queryByTestId('help-card-concern-inbox')).not.toBeInTheDocument();
  });
});
