import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import GroupTile from '../GroupTile';

describe('GroupTile', () => {
  it('shows program membership role for group members', () => {
    render(
      <GroupTile
        title="Bunk Maple"
        subtitle="Summer 2026"
        assignments={[{
          id: 1,
          kind: 'group_membership',
          person_name: 'Sam Lee',
          membership_role: 'counselor',
          is_active: true,
          start_date: '2026-06-01',
          end_date: null,
        }]}
        selectedAssignmentIds={new Set()}
        onToggleAssignment={vi.fn()}
        onToggleAllAssignments={vi.fn()}
        onEndSelected={vi.fn()}
        onAssignPerson={vi.fn()}
      />,
    );

    expect(screen.getByText('Sam Lee')).toBeInTheDocument();
    expect(screen.getByText('Counselor')).toBeInTheDocument();
  });

  it('shows roles on supervision rows', () => {
    render(
      <GroupTile
        title="Sue Per"
        assignments={[{
          id: 2,
          kind: 'supervision',
          supervisor_name: 'Sue Per',
          supervisor_role: 'unit_head',
          target_membership_name: 'Ta Rget',
          target_membership_role: 'counselor',
          is_active: true,
          start_date: '2026-06-01',
          end_date: null,
        }]}
        selectedAssignmentIds={new Set()}
        onToggleAssignment={vi.fn()}
        onToggleAllAssignments={vi.fn()}
        onEndSelected={vi.fn()}
        onAssignPerson={vi.fn()}
      />,
    );

    expect(screen.getByText('Sue Per → Ta Rget')).toBeInTheDocument();
    expect(screen.getByText('Unit Head')).toBeInTheDocument();
    expect(screen.getByText('Counselor')).toBeInTheDocument();
  });
});
