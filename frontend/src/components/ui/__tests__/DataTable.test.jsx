import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import DataTable from '../DataTable';
import EmptyState from '../EmptyState';

const ROWS = [
  { id: 1, name: 'Ava Feldman' },
  { id: 2, name: 'Noah Katz' },
];

const COLUMNS = [{ key: 'name', header: 'Name', render: (r) => r.name }];

function renderTable(props = {}) {
  return render(<DataTable columns={COLUMNS} rows={ROWS} {...props} />);
}

describe('DataTable', () => {
  it('renders a header cell per column and a row per record', () => {
    renderTable();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Ava Feldman')).toBeInTheDocument();
    expect(screen.getByText('Noah Katz')).toBeInTheDocument();
  });

  it('renders the empty node instead of a table when there are no rows', () => {
    render(
      <DataTable columns={COLUMNS} rows={[]} empty={<EmptyState title="Nobody matches" />} />,
    );
    expect(screen.getByText('Nobody matches')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('separates row-click preview from checkbox selection', async () => {
    const onRowClick = vi.fn();
    const onToggle = vi.fn();
    renderTable({
      onRowClick,
      selection: { selected: new Set(), onToggle, onToggleAll: vi.fn() },
    });

    await userEvent.click(screen.getByLabelText('Select row 1'));
    expect(onToggle).toHaveBeenCalledWith(1);
    expect(onRowClick).not.toHaveBeenCalled();

    await userEvent.click(screen.getByText('Ava Feldman'));
    expect(onRowClick).toHaveBeenCalledWith(ROWS[0]);
  });

  it('checks select-all only when every visible row is selected', () => {
    const { rerender } = renderTable({
      selection: { selected: new Set([1]), onToggle: vi.fn(), onToggleAll: vi.fn() },
    });
    expect(screen.getByTestId('data-table-select-all')).not.toBeChecked();

    rerender(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        selection={{ selected: new Set([1, 2]), onToggle: vi.fn(), onToggleAll: vi.fn() }}
      />,
    );
    expect(screen.getByTestId('data-table-select-all')).toBeChecked();
  });
});
