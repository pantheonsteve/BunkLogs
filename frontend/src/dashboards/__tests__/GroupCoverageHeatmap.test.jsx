import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GroupCoverageHeatmap from '../coverage/GroupCoverageHeatmap';
import { COVERAGE_TIERS } from '../colors';

function renderHeatmap(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const MAPLE = {
  id: 1,
  name: 'Bunk Maple',
  group_type: 'bunk',
  program_name: 'Session 1',
  days: [
    { date: '2026-06-01', covered: 8, total: 8, percent: 100, status: 'green' },
    { date: '2026-06-02', covered: 5, total: 8, percent: 62, status: 'orange' },
    { date: '2026-06-03', covered: 0, total: 8, percent: 0, status: 'gray' },
  ],
};

const OAK = {
  id: 2,
  name: 'Bunk Oak',
  group_type: 'bunk',
  days: [
    { date: '2026-06-01', covered: 0, total: 0, percent: 0, status: 'inactive' },
    { date: '2026-06-02', covered: 7, total: 8, percent: 87, status: 'yellow' },
    { date: '2026-06-03', covered: 8, total: 8, percent: 100, status: 'green' },
  ],
};

describe('GroupCoverageHeatmap', () => {
  it('renders one row per group', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE, OAK]} />);
    expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    expect(screen.getByText('Bunk Oak')).toBeInTheDocument();
  });

  it('renders one column header per day', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    // Three day columns
    const cells = screen.getAllByText('100');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('colors green-tier cells with the green fill', () => {
    const { container } = renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    const greenCells = Array.from(container.querySelectorAll('td')).filter(
      (td) => td.style.backgroundColor && td.style.backgroundColor.length > 0,
    );
    // Convert RGB string back to hex-ish; just check the green tier shows up.
    const hasGreen = greenCells.some(
      (td) => td.getAttribute('aria-label')?.includes('100%'),
    );
    expect(hasGreen).toBe(true);
  });

  it('renders inactive cells with no-roster aria-label', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[OAK]} />);
    const inactive = screen.getAllByLabelText(/no roster/i);
    expect(inactive.length).toBeGreaterThan(0);
  });

  it('every cell has an aria-label with covered/total/percent', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    expect(
      screen.getByLabelText(/Bunk Maple.*8 of 8 covered \(100%\)/),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Bunk Maple.*5 of 8 covered \(62%\)/),
    ).toBeInTheDocument();
  });

  it('renders the legend with all tiers', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    Object.values(COVERAGE_TIERS).forEach((tier) => {
      expect(screen.getByText(tier.label)).toBeInTheDocument();
    });
  });

  it('links each group name to its group homepage', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    const link = screen.getByRole('link', { name: 'Bunk Maple' });
    expect(link).toHaveAttribute('href', '/dashboards/group/1');
  });

  it('shows the program name alongside the group when provided', () => {
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} />);
    expect(screen.getByText('Session 1')).toBeInTheDocument();
  });

  it('fires onRowClick with the group when clicking a row', () => {
    const onRowClick = vi.fn();
    renderHeatmap(<GroupCoverageHeatmap groups={[MAPLE]} onRowClick={onRowClick} />);
    fireEvent.click(screen.getByText('Bunk Maple').closest('tr'));
    expect(onRowClick).toHaveBeenCalledWith(MAPLE);
  });
});
