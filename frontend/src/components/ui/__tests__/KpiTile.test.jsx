import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import KpiTile from '../KpiTile';

describe('KpiTile', () => {
  it('renders label, value, unit and a directional delta', () => {
    render(
      <KpiTile label="Avg camper rating" value="4.1" unit="/ 5" delta="0.2" deltaDirection="down" sub="vs last week" />,
    );
    expect(screen.getByText('Avg camper rating')).toBeInTheDocument();
    expect(screen.getByText('4.1')).toBeInTheDocument();
    expect(screen.getByText('/ 5')).toBeInTheDocument();
    expect(screen.getByText('vs last week')).toBeInTheDocument();
    const delta = screen.getByTestId('kpi-delta');
    expect(delta).toHaveTextContent('▼ down 0.2');
    expect(delta.className).toContain('text-danger-ink');
  });
});
