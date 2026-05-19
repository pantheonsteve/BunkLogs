import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Users } from 'lucide-react';

import EmptyState from '../EmptyState';

describe('EmptyState (3.31)', () => {
  it('renders the title', () => {
    render(<EmptyState title="No groups yet" />);
    expect(screen.getByText('No groups yet')).toBeInTheDocument();
  });

  it('renders an icon when supplied', () => {
    const { container } = render(<EmptyState icon={Users} title="Empty" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders children body content under the title', () => {
    render(
      <EmptyState title="No templates">
        Create one to get started.
      </EmptyState>,
    );
    expect(screen.getByText(/create one to get started/i)).toBeInTheDocument();
  });

  it('renders an action node when supplied', () => {
    render(
      <EmptyState
        title="Empty"
        action={<a href="/admin/templates/new">New template</a>}
      />,
    );
    expect(screen.getByText('New template')).toBeInTheDocument();
  });

  it('applies the standard "text-center py-12" container classes', () => {
    const { container } = render(<EmptyState title="X" data-testid="es" />);
    const node = screen.getByTestId('es');
    expect(node.className).toContain('text-center');
    expect(node.className).toContain('py-12');
    void container;
  });
});
