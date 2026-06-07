import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GroupDisplayName, { groupContextLine } from '../GroupDisplayName';

describe('GroupDisplayName', () => {
  it('shows program and parent as context line', () => {
    render(
      <GroupDisplayName
        group={{
          name: 'Bunk Maple',
          program_name: 'Session 1',
          parent_name: 'Unit Aleph',
        }}
      />,
    );
    expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    expect(screen.getByTestId('group-display-context')).toHaveTextContent('Session 1 · Unit Aleph');
  });

  it('groupContextLine joins program and parent', () => {
    expect(groupContextLine({
      program_name: 'Session 2',
      parent_name: 'Unit Bet',
    })).toBe('Session 2 · Unit Bet');
  });
});
