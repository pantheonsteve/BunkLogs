import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GroupRoster from '../GroupRoster';

const ROSTER = [
  { person_id: 1, name: 'Pat Lee', role_in_group: 'author', membership_role: 'counselor' },
  { person_id: 2, name: 'Alex Kim', role_in_group: 'subject', membership_role: 'camper' },
  { person_id: 3, name: 'Bree Ng', role_in_group: 'subject', membership_role: null },
];

describe('GroupRoster', () => {
  it('lists each member with a prettified program role and group role', () => {
    render(<GroupRoster roster={ROSTER} />);
    expect(screen.getByText('Roster (3)')).toBeInTheDocument();
    expect(screen.getByText('Pat Lee')).toBeInTheDocument();
    expect(screen.getByText('Counselor')).toBeInTheDocument();
    expect(screen.getByText('Camper')).toBeInTheDocument();
    // Author rows are labeled "Author"; subjects as "Member".
    expect(screen.getByText('Author')).toBeInTheDocument();
    expect(screen.getAllByText('Member')).toHaveLength(2);
  });

  it('renders an em-dash when a member has no program membership role', () => {
    render(<GroupRoster roster={[ROSTER[2]]} />);
    expect(screen.getByText('\u2014')).toBeInTheDocument();
  });

  it('shows an empty state when there are no members', () => {
    render(<GroupRoster roster={[]} />);
    expect(screen.getByText('Roster (0)')).toBeInTheDocument();
    expect(screen.getByText(/no active members/i)).toBeInTheDocument();
  });

  it('collapses and expands when collapsible', async () => {
    const user = userEvent.setup();
    render(<GroupRoster roster={ROSTER} collapsible defaultExpanded={false} />);
    expect(screen.queryByText('Pat Lee')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('group-roster-toggle'));
    expect(screen.getByText('Pat Lee')).toBeInTheDocument();
  });

  it('tolerates a missing roster prop', () => {
    render(<GroupRoster />);
    expect(screen.getByText('Roster (0)')).toBeInTheDocument();
  });
});
