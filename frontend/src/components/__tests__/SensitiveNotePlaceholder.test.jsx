import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SensitiveNotePlaceholder from '../SensitiveNotePlaceholder';

describe('SensitiveNotePlaceholder', () => {
  it('renders singular count and gating role', () => {
    render(<SensitiveNotePlaceholder count={1} gatingRole="Camper Care" />);
    expect(screen.getByTestId('sensitive-note-placeholder')).toHaveTextContent(
      '1 sensitive note (Camper Care)',
    );
  });

  it('renders plural count', () => {
    render(<SensitiveNotePlaceholder count={3} gatingRole="Camper Care" />);
    expect(screen.getByTestId('sensitive-note-placeholder')).toHaveTextContent(
      '3 sensitive notes (Camper Care)',
    );
  });

  it('returns null when count is zero', () => {
    const { container } = render(
      <SensitiveNotePlaceholder count={0} gatingRole="Camper Care" />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
