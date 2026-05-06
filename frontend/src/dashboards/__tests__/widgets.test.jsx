import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RatingHeadlineWidget from '../widgets/RatingHeadlineWidget';
import CategoryRadarWidget from '../widgets/CategoryRadarWidget';
import HighlightFeedWidget from '../widgets/HighlightFeedWidget';
import ImprovementFeedWidget from '../widgets/ImprovementFeedWidget';
import ConcernQueueWidget from '../widgets/ConcernQueueWidget';
import TextResponseListWidget from '../widgets/TextResponseListWidget';
import ItemCloudWidget from '../widgets/ItemCloudWidget';
import RatingDistributionWidget from '../widgets/RatingDistributionWidget';
import RatingTableWidget from '../widgets/RatingTableWidget';
import ChoiceBarChartWidget from '../widgets/ChoiceBarChartWidget';
import YesNoBreakdownWidget from '../widgets/YesNoBreakdownWidget';

// ── RatingHeadlineWidget ───────────────────────────────────────────────────────

describe('RatingHeadlineWidget', () => {
  const field = {
    key: 'overall',
    scale: [1, 5],
    data: { mean: 3.7, prior_mean: 3.2, trend: 'up', response_count: 6, distribution: {} },
  };

  it('shows mean value', () => {
    render(<RatingHeadlineWidget field={field} label="Overall" />);
    expect(screen.getByText('3.7')).toBeInTheDocument();
  });

  it('shows prior period mean', () => {
    render(<RatingHeadlineWidget field={field} label="Overall" />);
    expect(screen.getByText(/prior period/i)).toBeInTheDocument();
    expect(screen.getByText(/3\.2/)).toBeInTheDocument();
  });

  it('shows response count', () => {
    render(<RatingHeadlineWidget field={field} label="Overall" />);
    expect(screen.getByText(/6 responses/i)).toBeInTheDocument();
  });

  it('shows dash when no data', () => {
    render(<RatingHeadlineWidget field={{ key: 'x', scale: [1, 5], data: { mean: null } }} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});

// ── CategoryRadarWidget ───────────────────────────────────────────────────────

describe('CategoryRadarWidget', () => {
  const field = {
    key: 'pulse',
    scale: [1, 4],
    data: {
      categories: [
        { key: 'morale', mean: 3.5, prior_mean: 3.0, trend: 'up', response_count: 5, distribution: {} },
        { key: 'energy', mean: 2.8, prior_mean: 3.1, trend: 'down', response_count: 5, distribution: {} },
      ],
    },
  };

  it('renders all categories', () => {
    render(<CategoryRadarWidget field={field} />);
    expect(screen.getByText('morale')).toBeInTheDocument();
    expect(screen.getByText('energy')).toBeInTheDocument();
  });

  it('shows mean values', () => {
    render(<CategoryRadarWidget field={field} />);
    expect(screen.getByText('3.5')).toBeInTheDocument();
    expect(screen.getByText('2.8')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<CategoryRadarWidget field={{ key: 'x', data: { categories: [] } }} />);
    expect(screen.getByText(/no data/i)).toBeInTheDocument();
  });
});

// ── HighlightFeedWidget ───────────────────────────────────────────────────────

describe('HighlightFeedWidget', () => {
  const field = {
    key: 'wins',
    data: {
      items: [
        { text: 'Teamwork', count: 4 },
        { text: 'Communication', count: 2 },
      ],
      total_mentions: 6,
    },
  };

  it('renders items', () => {
    render(<HighlightFeedWidget field={field} />);
    expect(screen.getByText('Teamwork')).toBeInTheDocument();
    expect(screen.getByText('Communication')).toBeInTheDocument();
  });

  it('shows total mentions', () => {
    render(<HighlightFeedWidget field={field} />);
    expect(screen.getByText(/6 mentions/i)).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<HighlightFeedWidget field={{ key: 'x', data: { items: [], total_mentions: 0 } }} />);
    expect(screen.getByText(/none submitted/i)).toBeInTheDocument();
  });
});

// ── ImprovementFeedWidget ─────────────────────────────────────────────────────

describe('ImprovementFeedWidget', () => {
  it('renders items with growth framing', () => {
    const field = {
      key: 'growth',
      data: { items: [{ text: 'Time management', count: 3 }], total_mentions: 3 },
    };
    render(<ImprovementFeedWidget field={field} />);
    expect(screen.getByText('Time management')).toBeInTheDocument();
  });
});

// ── ConcernQueueWidget ────────────────────────────────────────────────────────

describe('ConcernQueueWidget', () => {
  const field = {
    key: 'concerns',
    data: {
      items: [
        { reflection_id: 1, person_id: 5, period_end: '2026-06-14', text: 'Concern text here', is_read: false },
      ],
      total: 1,
    },
  };

  it('shows unread badge', () => {
    render(<ConcernQueueWidget field={field} />);
    expect(screen.getByText(/1 new/i)).toBeInTheDocument();
  });

  it('expands to show text on click', () => {
    render(<ConcernQueueWidget field={field} />);
    expect(screen.queryByText('Concern text here')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/Person 5/i));
    expect(screen.getByText('Concern text here')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<ConcernQueueWidget field={{ key: 'x', data: { items: [], total: 0 } }} />);
    expect(screen.getByText(/no concerns/i)).toBeInTheDocument();
  });
});

// ── TextResponseListWidget ────────────────────────────────────────────────────

describe('TextResponseListWidget', () => {
  const field = {
    key: 'notes',
    data: {
      items: [
        { reflection_id: 1, person_id: 1, period_end: '2026-06-14', text: 'Short note', is_read: false },
      ],
      total: 1,
    },
  };

  it('renders text items', () => {
    render(<TextResponseListWidget field={field} />);
    expect(screen.getByText('Short note')).toBeInTheDocument();
  });

  it('shows response count', () => {
    render(<TextResponseListWidget field={field} />);
    expect(screen.getByText(/1 response/i)).toBeInTheDocument();
  });
});

// ── ItemCloudWidget ───────────────────────────────────────────────────────────

describe('ItemCloudWidget', () => {
  const field = {
    key: 'items',
    data: {
      items: [{ text: 'Creativity', count: 5 }, { text: 'Initiative', count: 2 }],
      total_mentions: 7,
    },
  };

  it('renders items as tags', () => {
    render(<ItemCloudWidget field={field} />);
    expect(screen.getByText(/creativity/i)).toBeInTheDocument();
    expect(screen.getByText(/initiative/i)).toBeInTheDocument();
  });
});

// ── RatingDistributionWidget ──────────────────────────────────────────────────

describe('RatingDistributionWidget', () => {
  const field = {
    key: 'single',
    data: {
      mean: 3.5,
      prior_mean: 3.0,
      trend: 'up',
      response_count: 4,
      distribution: { '1': 0, '2': 0, '3': 2, '4': 2, '5': 0 },
    },
  };

  it('shows mean', () => {
    render(<RatingDistributionWidget field={field} />);
    expect(screen.getByText('3.5')).toBeInTheDocument();
  });
});

// ── RatingTableWidget ─────────────────────────────────────────────────────────

describe('RatingTableWidget', () => {
  const field = {
    key: 'group',
    data: {
      categories: [
        { key: 'morale', mean: 3.5, response_count: 5, distribution: {} },
        { key: 'energy', mean: 2.8, response_count: 4, distribution: {} },
      ],
    },
  };

  it('renders category rows', () => {
    render(<RatingTableWidget field={field} />);
    expect(screen.getByText('morale')).toBeInTheDocument();
    expect(screen.getByText('energy')).toBeInTheDocument();
    expect(screen.getByText('3.50')).toBeInTheDocument();
  });
});

// ── ChoiceBarChartWidget ──────────────────────────────────────────────────────

describe('ChoiceBarChartWidget', () => {
  const field = {
    key: 'pick',
    data: {
      choices: [
        { option: 'Option A', count: 5 },
        { option: 'Option B', count: 3 },
      ],
      response_count: 8,
    },
  };

  it('renders choices', () => {
    render(<ChoiceBarChartWidget field={field} />);
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option B')).toBeInTheDocument();
  });
});

// ── YesNoBreakdownWidget ──────────────────────────────────────────────────────

describe('YesNoBreakdownWidget', () => {
  const field = {
    key: 'yn',
    data: { yes_count: 6, no_count: 2, yes_pct: 0.75 },
  };

  it('shows yes and no counts', () => {
    render(<YesNoBreakdownWidget field={field} />);
    expect(screen.getByText(/Yes/)).toBeInTheDocument();
    expect(screen.getByText(/No/)).toBeInTheDocument();
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<YesNoBreakdownWidget field={{ key: 'x', data: { yes_count: 0, no_count: 0, yes_pct: null } }} />);
    expect(screen.getByText(/no responses/i)).toBeInTheDocument();
  });
});
