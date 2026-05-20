import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import EditedIndicator from '../EditedIndicator';

describe('EditedIndicator', () => {
  it('renders nothing when editedAt is missing', () => {
    const { container } = render(<EditedIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it('hides the editor name for non-admin viewers', () => {
    render(
      <EditedIndicator
        user={{ is_staff: false, is_superuser: false }}
        editedAt="2026-05-19T12:00:00Z"
        editorName="Alex Admin"
      />,
    );
    const el = screen.getByTestId('edited-indicator');
    expect(el).toHaveAttribute('data-admin-viewer', 'false');
    expect(el).not.toHaveTextContent('Alex Admin');
    expect(el.tagName).toBe('SPAN');
  });

  it('reveals editor name for org admins', () => {
    render(
      <EditedIndicator
        isAdmin
        editedAt="2026-05-19T12:00:00Z"
        editorName="Alex Admin"
      />,
    );
    expect(screen.getByTestId('edited-indicator')).toHaveTextContent(/Alex Admin/);
  });

  it('renders as a button with onOpenAuditTrail handler for admins', () => {
    const onOpen = vi.fn();
    render(
      <EditedIndicator
        user={{ is_superuser: true }}
        editedAt="2026-05-19T12:00:00Z"
        editorName="Alex"
        onOpenAuditTrail={onOpen}
      />,
    );
    const btn = screen.getByTestId('edited-indicator');
    expect(btn.tagName).toBe('BUTTON');
    fireEvent.click(btn);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it('respects an explicit showEditor=false override even for admins', () => {
    render(
      <EditedIndicator
        isAdmin
        editedAt="2026-05-19T12:00:00Z"
        editorName="Alex"
        showEditor={false}
      />,
    );
    expect(screen.getByTestId('edited-indicator')).not.toHaveTextContent('Alex');
  });
});
