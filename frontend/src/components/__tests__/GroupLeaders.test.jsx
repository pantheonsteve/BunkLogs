import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import GroupLeaders from '../GroupLeaders';

describe('GroupLeaders', () => {
  it('shows authors with roles, supervisors first, and hides subjects', () => {
    render(
      <GroupLeaders
        roster={[
          { person_id: 1, name: 'Ezra Timmerman', role_in_group: 'author', membership_role: 'madrich' },
          { person_id: 2, name: 'Sara Slager', role_in_group: 'author', membership_role: 'faculty' },
          { person_id: 3, name: 'Abby Wexler', role_in_group: 'subject', membership_role: 'student' },
        ]}
      />,
    );
    const items = within(screen.getByTestId('group-leaders')).getAllByRole('listitem');
    expect(items.map((li) => li.textContent)).toEqual([
      'SSSara SlagerFaculty',
      'ETEzra TimmermanMadrich',
    ]);
    expect(screen.queryByText('Abby Wexler')).not.toBeInTheDocument();
  });

  it('renders nothing without authors', () => {
    const { container } = render(<GroupLeaders roster={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
