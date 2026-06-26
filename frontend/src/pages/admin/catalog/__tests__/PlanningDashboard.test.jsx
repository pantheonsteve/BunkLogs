import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import PlanningDashboard from '../PlanningDashboard';

const fetchCatalogPlanning = vi.fn();
const fetchCatalogTree = vi.fn();

vi.mock('../../../../api/admin', () => ({
  fetchCatalogPlanning: (...a) => fetchCatalogPlanning(...a),
  fetchCatalogTree: (...a) => fetchCatalogTree(...a),
  downloadCatalogPlanningCsv: vi.fn(),
}));

// chart.js needs a real canvas context; stub it out for jsdom.
vi.mock('chart.js', () => ({
  Chart: class {
    constructor() {}
    destroy() {}
  },
}));
vi.mock('chart.js/auto', () => ({}));

const PLANNING = {
  group_by: 'item',
  totals: { quantity: 10, request_count: 3, group_count: 2 },
  rows: [
    { key: 'item:1', label: 'Toothbrush', store: 'Camper Care', request_type: 'Items', quantity: 7, request_count: 2 },
    { key: 'item:2', label: 'Soap', store: 'Camper Care', request_type: 'Items', quantity: 3, request_count: 1 },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/catalog/planning']}>
      <PlanningDashboard />
    </MemoryRouter>,
  );
}

describe('PlanningDashboard', () => {
  beforeEach(() => {
    fetchCatalogPlanning.mockReset();
    fetchCatalogTree.mockReset();
    fetchCatalogTree.mockResolvedValue({ stores: [{ id: 1, name: 'Camper Care' }] });
    fetchCatalogPlanning.mockResolvedValue(PLANNING);
  });

  it('renders aggregated rows and totals', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('planning-table')).toBeInTheDocument());
    expect(screen.getByText('Toothbrush')).toBeInTheDocument();
    expect(screen.getByText('Soap')).toBeInTheDocument();
    expect(screen.getByTestId('planning-total-qty')).toHaveTextContent('10');
  });

  it('shows an empty state when there is no data', async () => {
    fetchCatalogPlanning.mockResolvedValue({ rows: [], totals: {} });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('planning-empty')).toBeInTheDocument());
  });

  it('sorts the table when a column header is clicked', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByTestId('planning-table')).toBeInTheDocument());

    const firstCell = () =>
      within(within(screen.getByTestId('planning-table')).getAllByRole('row')[1]).getAllByRole('cell')[0];

    // Defaults to quantity desc → Toothbrush (7) before Soap (3).
    expect(firstCell()).toHaveTextContent('Toothbrush');

    // Sort by label ascending → Soap first.
    await user.click(screen.getByTestId('planning-sort-label'));
    await waitFor(() => expect(firstCell()).toHaveTextContent('Soap'));
  });
});
