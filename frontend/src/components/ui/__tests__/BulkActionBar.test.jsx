import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import BulkActionBar from '../BulkActionBar';
import Button from '../Button';

describe('BulkActionBar', () => {
  it('renders nothing at zero selected, so destructive actions are never live on an empty selection', () => {
    render(
      <BulkActionBar count={0}>
        <Button variant="danger">Remove</Button>
      </BulkActionBar>,
    );
    expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });

  it('shows the selected count and its actions once rows are selected', () => {
    render(
      <BulkActionBar count={3}>
        <Button variant="danger">Remove 3 students</Button>
      </BulkActionBar>,
    );
    expect(screen.getByText('3 selected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove 3 students' })).toBeInTheDocument();
  });

  it('clears the selection', async () => {
    const onClear = vi.fn();
    render(<BulkActionBar count={2} onClear={onClear} />);
    await userEvent.click(screen.getByRole('button', { name: /clear/i }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
