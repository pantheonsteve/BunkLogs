import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CamperDashboard from '../CamperDashboard';

function renderDash(data, props = {}) {
  return render(
    <MemoryRouter>
      <CamperDashboard data={data} {...props} />
    </MemoryRouter>,
  );
}

const trendData = {
  series: [
    {
      label: 'social',
      field_key: 'category_ratings',
      field_type: 'rating_group',
      scale_max: 5,
      points: [
        { date: '2026-06-30', value: 4, reflection_id: 11 },
        { date: '2026-07-01', value: null, reflection_id: null },
        { date: '2026-07-02', value: 5, reflection_id: 12 },
      ],
    },
    {
      label: 'overall',
      field_key: 'overall',
      field_type: 'single_rating',
      scale_max: 5,
      points: [
        { date: '2026-06-30', value: 3, reflection_id: 11 },
        { date: '2026-07-01', value: null, reflection_id: null },
        { date: '2026-07-02', value: 4, reflection_id: 12 },
      ],
    },
  ],
  scale_max: 5,
  period: { start: '2026-06-30', end: '2026-07-02' },
};

const baseData = {
  header: {
    camper: { id: 1, first_name: 'Jamie', last_name: 'Smith', preferred_name: 'J' },
    date: '2026-07-02',
  },
  trend: trendData,
  today_reflection: null,
  today_scores: [],
  today_flags: [],
  specialist_reports: { items: [], sensitive_excluded_count: 0 },
  camper_care_notes: { items: [], sensitive_excluded_count: 0 },
};

describe('CamperDashboard', () => {
  it('renders the trend grid with one row per series', () => {
    renderDash(baseData);
    expect(screen.getByTestId('trend-grid')).toBeInTheDocument();
    expect(screen.getByTestId('trend-toggle-social')).toBeInTheDocument();
    expect(screen.getByTestId('trend-toggle-overall')).toBeInTheDocument();
  });

  it('renders empty cells when a day has no reflection', () => {
    renderDash(baseData);
    expect(screen.getAllByTestId('trend-cell-empty').length).toBeGreaterThan(0);
  });

  it('toggles a series off when its legend chip is clicked', async () => {
    renderDash(baseData);
    const user = userEvent.setup();
    const toggle = screen.getByTestId('trend-toggle-social');
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows flagged-in-reflection section when flags are present', () => {
    const data = {
      ...baseData,
      today_flags: [{
        key: 'request_help',
        value: true,
        prompts: { en: 'Want to request a check-in?' },
      }],
    };
    renderDash(data);
    expect(screen.getByTestId('section-today-flags')).toBeInTheDocument();
    expect(screen.getByTestId('flag-request_help')).toHaveTextContent('Want to request a check-in?');
  });

  it('renders today\'s scores as colored pills', () => {
    const data = {
      ...baseData,
      today_scores: [
        { label: 'social', value: 4, scale_max: 5 },
        { label: 'behavioral', value: null, scale_max: 5 },
      ],
    };
    renderDash(data);
    expect(screen.getByTestId('score-pill-social')).toHaveTextContent('4');
    expect(screen.getByTestId('score-pill-behavioral')).toHaveTextContent('—');
  });

  it('renders today\'s reflection fields in template order', () => {
    const data = {
      ...baseData,
      today_reflection: {
        id: 7,
        author: 'Pat L.',
        language: 'en',
        submitted_at: '2026-07-02T12:00:00Z',
        team_visibility: 'team',
        fields: [
          { key: 'wins', type: 'textarea', prompts: { en: 'Wins?' }, answer: 'Great day' },
          { key: 'overall', type: 'single_rating', prompts: { en: 'Overall?' }, scale: { max: 5 }, answer: 4 },
        ],
      },
    };
    renderDash(data);
    expect(screen.getByTestId('section-today-reflection')).toBeInTheDocument();
    expect(screen.getByTestId('reflection-field-wins')).toHaveTextContent('Great day');
    expect(screen.getByTestId('reflection-field-overall')).toHaveTextContent('4');
  });

  it('renders sensitive-excluded count for notes when present', () => {
    const data = {
      ...baseData,
      specialist_reports: { items: [], sensitive_excluded_count: 2 },
    };
    renderDash(data);
    const section = screen.getByTestId('section-specialist-reports');
    expect(section).toHaveTextContent('2 sensitive notes not visible');
  });

  it('emits date / range change callbacks', async () => {
    const onDate = vi.fn();
    const onRange = vi.fn();
    renderDash(baseData, { onDateChange: onDate, onRangeChange: onRange });
    const user = userEvent.setup();
    const dateInput = screen.getByTestId('camper-dashboard-date');
    await user.clear(dateInput);
    await user.type(dateInput, '2026-06-15');
    expect(onDate).toHaveBeenCalled();
    const rangeSelect = screen.getByTestId('camper-dashboard-range');
    await user.selectOptions(rangeSelect, 'this_week');
    expect(onRange).toHaveBeenCalledWith('this_week');
  });
});
