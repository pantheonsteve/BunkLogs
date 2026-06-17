import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ScorePieChart from '../ScorePieChart';

describe('ScorePieChart', () => {
  it('renders a filled circle for a single-score distribution', () => {
    const { container } = render(
      <ScorePieChart distribution={{ 1: 1, 2: 0, 3: 0, 4: 0 }} scaleMax={4} size={96} />,
    );
    expect(container.querySelector('circle')).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Score distribution: 1: 1' })).toBeInTheDocument();
  });

  it('renders arc slices for multi-bucket distributions', () => {
    const { container } = render(
      <ScorePieChart distribution={{ 2: 1, 4: 1 }} scaleMax={5} size={96} />,
    );
    expect(container.querySelectorAll('path').length).toBe(2);
    expect(container.querySelector('circle')).toBeFalsy();
  });
});
