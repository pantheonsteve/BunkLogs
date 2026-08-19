/**
 * Rating trend chart — Step 4_9 §4.4.
 *
 * The one thing that must not regress is the y-axis: it is pinned to the
 * template's declared scale, so a 3→4 move never renders as a dramatic climb
 * off a fitted axis.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import RatingTrendChart from '../RatingTrendChart';

const chartCtor = vi.fn();
vi.mock('chart.js', () => ({
  Chart: class {
    constructor(...args) { chartCtor(...args); }
    destroy() {}
  },
}));
vi.mock('chart.js/auto', () => ({}));

HTMLCanvasElement.prototype.getContext = () => ({});

const series = {
  trend_key: 'madrich_weekly.ratings.initiative',
  field_key: 'ratings',
  category_key: 'initiative',
  label: 'Initiative',
  scale_min: 1,
  scale_max: 4,
  points: [
    { date: '2026-09-06', value: 3, reflection_id: 1 },
    { date: '2026-09-13', value: 4, reflection_id: 2 },
  ],
};

function chartConfig() {
  return chartCtor.mock.calls.at(-1)[1];
}

beforeEach(() => {
  chartCtor.mockReset();
});

describe('RatingTrendChart', () => {
  it('pins the y-axis to the declared scale rather than the data range', () => {
    render(<RatingTrendChart series={series} />);
    const { scales } = chartConfig().options;
    expect(scales.y.min).toBe(1);
    expect(scales.y.max).toBe(4);
  });

  it('plots a single submission as a point with no line', () => {
    render(<RatingTrendChart series={{ ...series, points: [series.points[0]] }} />);
    expect(chartConfig().data.datasets[0].showLine).toBe(false);
  });

  it('explains an empty series instead of rendering an empty chart', () => {
    render(<RatingTrendChart series={{ ...series, points: [] }} />);
    expect(chartCtor).not.toHaveBeenCalled();
    expect(screen.getByTestId(`trend-empty-${series.trend_key}`)).toHaveTextContent(
      'No ratings yet',
    );
  });

  it('describes the series for screen readers, including the scale', () => {
    render(<RatingTrendChart series={series} />);
    expect(
      screen.getByRole('img', { name: /Initiative: 2 ratings on a 1 to 4 scale/ }),
    ).toBeInTheDocument();
  });
});
