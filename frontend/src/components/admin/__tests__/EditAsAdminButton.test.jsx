import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../api', () => ({
  default: { post: vi.fn() },
}));
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import api from '../../../api';
import { useAuth } from '../../../auth/AuthContext';
import EditAsAdminButton from '../EditAsAdminButton';

beforeEach(() => {
  api.post.mockReset();
  useAuth.mockReset();
});

describe('EditAsAdminButton', () => {
  it('renders nothing for non-admin viewers', () => {
    useAuth.mockReturnValue({ user: { role: 'counselor' } });
    const { container } = render(
      <EditAsAdminButton contentType="reflection" contentId="abc" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('requires a reason before submitting', async () => {
    useAuth.mockReturnValue({ user: { role: 'admin' } });
    render(<EditAsAdminButton contentType="reflection" contentId="abc" patchBuilder={() => ({ answers: { x: 1 } })} />);
    fireEvent.click(screen.getByTestId('edit-as-admin-button'));
    fireEvent.click(screen.getByTestId('edit-as-admin-submit'));
    expect(await screen.findByTestId('edit-as-admin-error')).toHaveTextContent(/reason is required/i);
    expect(api.post).not.toHaveBeenCalled();
  });

  it('posts to /admin/override-edit/ and calls onSaved on success', async () => {
    useAuth.mockReturnValue({ user: { is_staff: true } });
    api.post.mockResolvedValue({ data: { ok: true } });
    const onSaved = vi.fn();
    render(
      <EditAsAdminButton
        contentType="reflection"
        contentId="abc"
        onSaved={onSaved}
        patchBuilder={() => ({ answers: { x: 1 } })}
      />,
    );
    fireEvent.click(screen.getByTestId('edit-as-admin-button'));
    fireEvent.change(screen.getByTestId('edit-as-admin-reason'), {
      target: { value: 'parent requested redaction' },
    });
    fireEvent.click(screen.getByTestId('edit-as-admin-submit'));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/admin/override-edit/',
      expect.objectContaining({
        content_type: 'reflection',
        content_id: 'abc',
        reason: 'parent requested redaction',
        patch: { answers: { x: 1 } },
      }),
    );
    expect(onSaved).toHaveBeenCalledWith({ ok: true });
  });
});
