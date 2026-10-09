import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import AttentionCard from '../AttentionCard';

const rows = [1, 2, 3, 4, 5].map((id) => ({
  id,
  initials: `C${id}`,
  name: `Camper ${id}`,
  where: 'Bunk 8',
  age: `${id}d`,
  ageTone: id > 2 ? 'danger' : undefined,
  to: `/campers/${id}`,
}));

describe('AttentionCard', () => {
  it('shows three linked rows, the count, and a +N more link', () => {
    render(
      <MemoryRouter>
        <AttentionCard title="Camper Care Help" tone="danger" rows={rows} moreTo="/care" />
      </MemoryRouter>,
    );
    const card = screen.getByRole('region', { name: 'Camper Care Help' });
    expect(card).toHaveTextContent('5');
    expect(screen.getByRole('link', { name: /Camper 1/ })).toHaveAttribute('href', '/campers/1');
    expect(screen.getByRole('link', { name: /Camper 3/ })).toBeInTheDocument();
    expect(screen.queryByText('Camper 4')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: '+2 more' })).toHaveAttribute('href', '/care');
    expect(screen.getByText('3d').className).toContain('text-danger-ink');
  });

  it('renders the empty text when there are no rows', () => {
    render(
      <MemoryRouter>
        <AttentionCard title="Not on Camp" rows={[]} emptyText="Everyone is here." />
      </MemoryRouter>,
    );
    expect(screen.getByText('Everyone is here.')).toBeInTheDocument();
  });
});
