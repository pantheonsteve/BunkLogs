import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ScoreGrid from '../ScoreGrid';

const columns = [
  { label: 'social', field_key: 'category_ratings', field_type: 'rating_group', category_key: 'social', scale_max: 5, header: 'Social' },
  { label: 'behavioral', field_key: 'category_ratings', field_type: 'rating_group', category_key: 'behavioral', scale_max: 5, header: 'Behavioral' },
  { label: 'overall', field_key: 'overall', field_type: 'single_rating', category_key: null, scale_max: 5, header: 'Overall' },
  { label: 'notes', field_key: 'notes', field_type: 'textarea', category_key: null, scale_max: null, header: 'Description' },
];

const rows = [
  {
    camper: { id: 101, first_name: 'Alex', last_name: 'Smith', preferred_name: 'Alex' },
    cells: { social: 4, behavioral: 3, overall: 5, notes: 'Swam well today.' },
    reflection_id: 7,
  },
  {
    camper: { id: 102, first_name: 'Bo', last_name: 'Lee', preferred_name: null },
    cells: { social: null, behavioral: 2, overall: null, notes: null },
    reflection_id: null,
  },
];

function renderGrid(props = {}) {
  return render(
    <MemoryRouter>
      <ScoreGrid columns={columns} rows={rows} {...props} />
    </MemoryRouter>,
  );
}

describe('ScoreGrid', () => {
  it('renders one row per camper and one column per scored dimension', () => {
    renderGrid();
    expect(screen.getByTestId('score-row-101')).toBeInTheDocument();
    expect(screen.getByTestId('score-row-102')).toBeInTheDocument();
    expect(screen.getByTestId('score-col-social')).toBeInTheDocument();
    expect(screen.getByTestId('score-col-behavioral')).toBeInTheDocument();
    expect(screen.getByTestId('score-col-overall')).toBeInTheDocument();
    expect(screen.getByTestId('score-col-notes')).toBeInTheDocument();
  });

  it('renders text description cells for textarea columns', () => {
    renderGrid();
    expect(screen.getByText('Swam well today.')).toBeInTheDocument();
    const emptyTextCells = screen.getAllByTestId('text-cell-empty');
    expect(emptyTextCells.length).toBeGreaterThan(0);
  });

  it('renders no-data cells visually distinct from low scores', () => {
    renderGrid();
    const emptyCells = screen.getAllByTestId('score-cell-empty');
    expect(emptyCells.length).toBe(2);
    const filledCells = screen.getAllByTestId('score-cell');
    expect(filledCells.some((c) => c.getAttribute('data-value') === '2')).toBe(true);
  });

  it('renders the legend with one swatch per rating value plus no-data', () => {
    renderGrid();
    expect(screen.getByTestId('score-grid-legend')).toBeInTheDocument();
  });

  it('renders camper names as links to the configured dashboard path', () => {
    renderGrid({ camperLinkPrefix: '/unit-head/campers' });
    const links = screen.getAllByRole('link');
    expect(links.some((a) => a.getAttribute('href') === '/unit-head/campers/101')).toBe(true);
  });

  it('uses callback when onSelectCamper provided', async () => {
    const onSelect = vi.fn();
    renderGrid({ onSelectCamper: onSelect });
    const user = userEvent.setup();
    const button = screen.getByRole('button', { name: /alex/i });
    await user.click(button);
    expect(onSelect).toHaveBeenCalledWith(101);
  });

  it('renders an On Camp column with Yes/No when offCampIds is provided', () => {
    renderGrid({ offCampIds: new Set([102]) });
    expect(screen.getByTestId('score-col-oncamp')).toBeInTheDocument();
    const cells = screen.getAllByTestId('oncamp-cell');
    expect(cells).toHaveLength(2);
    expect(cells[0]).toHaveTextContent('Yes');
    expect(cells[1]).toHaveTextContent('No');
  });

  it('omits the On Camp column by default', () => {
    renderGrid();
    expect(screen.queryByTestId('score-col-oncamp')).not.toBeInTheDocument();
  });

  it('renders an empty state when no columns are present', () => {
    render(
      <MemoryRouter>
        <ScoreGrid columns={[]} rows={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('score-grid-empty')).toBeInTheDocument();
  });

  it('renders an empty state when no campers are rostered', () => {
    render(
      <MemoryRouter>
        <ScoreGrid columns={columns} rows={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('score-grid-no-campers')).toBeInTheDocument();
  });
});
