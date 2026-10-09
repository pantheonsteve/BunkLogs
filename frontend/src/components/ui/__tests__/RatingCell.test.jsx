import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import RatingCell from '../RatingCell';
import { NO_DATA_FILL, RATING_FILLS } from '../../../dashboards/colors';

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

describe('RatingCell', () => {
  it('prints the number on its palette fill and labels it', () => {
    render(<RatingCell value={3} label="Social" />);
    const cell = screen.getByRole('img', { name: 'Social 3 of 5' });
    expect(cell).toHaveTextContent('3');
    expect(cell.style.backgroundColor).toBe(hexToRgb(RATING_FILLS[3]));
  });

  it('renders the no-data swatch with an em dash for null', () => {
    render(<RatingCell value={null} label="Social" />);
    const cell = screen.getByRole('img', { name: 'Social no rating' });
    expect(cell).toHaveTextContent('—');
    expect(cell.style.backgroundColor).toBe(hexToRgb(NO_DATA_FILL));
  });
});
