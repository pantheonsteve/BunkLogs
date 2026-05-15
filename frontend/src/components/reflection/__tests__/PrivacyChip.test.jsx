import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PrivacyChip from '../PrivacyChip';

describe('PrivacyChip', () => {
  it('returns null for team visibility', () => {
    const { container } = render(<PrivacyChip teamVisibility="team" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null for missing visibility', () => {
    const { container } = render(<PrivacyChip />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a pill with "Filed privately" label on default size', () => {
    render(<PrivacyChip teamVisibility="supervisors_only" />);
    expect(screen.getByTestId('privacy-chip')).toBeInTheDocument();
    expect(screen.getByText(/Filed privately/i)).toBeInTheDocument();
  });

  it('renders an icon-only badge when size="icon"', () => {
    render(<PrivacyChip teamVisibility="supervisors_only" size="icon" />);
    const chip = screen.getByTestId('privacy-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('aria-label', 'Filed privately');
    // No visible text -- aria-label carries the meaning
    expect(screen.queryByText(/Filed privately/)).toBeNull();
  });
});
