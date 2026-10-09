import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProgressBar from '../ProgressBar';
import { COVERAGE_TIERS } from '../../../dashboards/colors';

describe('ProgressBar', () => {
  it('uses the light-green coverage fill at 95%', () => {
    render(<ProgressBar value={95} total={100} />);
    const fill = screen.getByTestId('progress-fill');
    expect(fill.style.width).toBe('95%');
    expect(fill).toHaveStyle({ backgroundColor: COVERAGE_TIERS.light_green.fill });
  });
});
