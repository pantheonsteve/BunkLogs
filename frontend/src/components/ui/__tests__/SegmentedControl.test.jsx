import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import SegmentedControl from '../SegmentedControl';

const OPTIONS = [
  { value: 'week', label: 'This week' },
  { value: 'session', label: 'Full session' },
];

function Harness({ onChange }) {
  const [value, setValue] = useState('week');
  return (
    <SegmentedControl
      ariaLabel="Period"
      options={OPTIONS}
      value={value}
      onChange={(v) => {
        onChange(v);
        setValue(v);
      }}
    />
  );
}

describe('SegmentedControl', () => {
  it('fires onChange and moves aria-pressed to the chosen option', async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    expect(screen.getByRole('group', { name: 'Period' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'This week' })).toHaveAttribute('aria-pressed', 'true');

    await userEvent.click(screen.getByRole('button', { name: 'Full session' }));

    expect(onChange).toHaveBeenCalledWith('session');
    expect(screen.getByRole('button', { name: 'Full session' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'This week' })).toHaveAttribute('aria-pressed', 'false');
  });
});
