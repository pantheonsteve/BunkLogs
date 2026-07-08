import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UnitHeadStaffReflectionsPage from '../UnitHeadStaffReflectionsPage';

vi.mock('../../../components/ui/SingleDatePicker', () => ({
  default: () => <div data-testid="date-picker-stub" />,
}));

const fetchUnitHeadStaffReflections = vi.fn();

vi.mock('../../../api/unitHead', () => ({
  fetchUnitHeadStaffReflections: (...args) => fetchUnitHeadStaffReflections(...args),
}));

beforeEach(() => {
  fetchUnitHeadStaffReflections.mockReset();
});

describe('UnitHeadStaffReflectionsPage', () => {
  it('renders supervised bunk staff reflections', async () => {
    fetchUnitHeadStaffReflections.mockResolvedValueOnce({
      header: { date: '2026-07-07', today: '2026-07-07' },
      bunks: [{
        id: 140,
        name: 'Bunk 4',
        slug: 'bunk-4',
        counselor_self_reflections: [{
          person_id: 1,
          counselor_name: 'Audrey Perrin',
          state: 'complete',
          reflection_id: 99,
          submitted_at: '2026-07-07T18:00:00Z',
          fields: [{ key: 'overall_day', label: 'Overall', value: 4 }],
          schema_fields: [{ key: 'overall_day', type: 'single_rating' }],
        }],
      }],
    });

    render(
      <MemoryRouter initialEntries={['/unit-head/staff-reflections?date=2026-07-07']}>
        <UnitHeadStaffReflectionsPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('uh-staff-refl-bunk-140')).toBeInTheDocument();
    });
    expect(screen.getByText('Staff Reflections')).toBeInTheDocument();
    expect(screen.getByText('Bunk 4')).toBeInTheDocument();
    expect(screen.getByText('Audrey Perrin')).toBeInTheDocument();
    expect(fetchUnitHeadStaffReflections).toHaveBeenCalledWith({ date: '2026-07-07' });
  });
});
