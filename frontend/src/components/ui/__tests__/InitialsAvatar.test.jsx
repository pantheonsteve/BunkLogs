import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import InitialsAvatar from '../InitialsAvatar';

describe('InitialsAvatar', () => {
  it('renders first and last initials on the brand chip', () => {
    render(<InitialsAvatar name="Avi Ben Rosen" />);
    const avatar = screen.getByRole('img', { name: 'Avi Ben Rosen' });
    expect(avatar).toHaveTextContent('AR');
    expect(avatar.className).toContain('bg-brand-soft');
  });
});
