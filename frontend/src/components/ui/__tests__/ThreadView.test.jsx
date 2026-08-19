/**
 * ThreadView — Step 4_9 §2.3.
 *
 * The component must not invent affordances: posting and resolving are shown
 * only when the backend says the viewer may, and a resolved thread is closed
 * to everyone.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThreadView from '../ThreadView';

const baseThread = {
  id: 7,
  field_label: 'One question or concern for your Director',
  body: 'How do I handle a kid who never participates?',
  routes_to: 'director',
  resolved_at: null,
  period: { start: '2026-09-07', end: '2026-09-13' },
  can_post: true,
  can_resolve: false,
  subject_person: { id: 3, display_name: 'Ari Rich' },
  messages: [
    {
      id: 1,
      author: { id: 3, display_name: 'Ari Rich', role: 'madrich' },
      body: 'Adding a bit more context.',
      is_self_update: true,
      created_at: '2026-09-14T12:00:00Z',
      edited_at: null,
    },
    {
      id: 2,
      author: { id: 9, display_name: 'Rabbi Gold', role: 'admin' },
      body: 'Let us talk Sunday.',
      is_self_update: false,
      created_at: '2026-09-15T12:00:00Z',
      edited_at: null,
    },
  ],
};

describe('ThreadView', () => {
  it('distinguishes the subject\'s own update from a supervisor reply', () => {
    render(<ThreadView thread={baseThread} onPost={vi.fn()} onResolve={vi.fn()} />);
    const messages = screen.getAllByTestId('thread-message');
    expect(messages[0]).toHaveAttribute('data-self-update', 'true');
    expect(messages[0]).toHaveTextContent('own update');
    expect(messages[1]).toHaveAttribute('data-self-update', 'false');
  });

  it('sends a reply and clears the composer', async () => {
    const onPost = vi.fn().mockResolvedValue(undefined);
    render(<ThreadView thread={baseThread} onPost={onPost} onResolve={vi.fn()} />);

    const composer = screen.getByTestId('thread-composer');
    await userEvent.type(composer, 'Thanks!');
    await userEvent.click(screen.getByTestId('thread-send'));

    expect(onPost).toHaveBeenCalledWith('Thanks!');
    expect(composer).toHaveValue('');
  });

  it('hides the composer when the viewer may not post', () => {
    render(
      <ThreadView thread={{ ...baseThread, can_post: false }} onPost={vi.fn()} onResolve={vi.fn()} />,
    );
    expect(screen.queryByTestId('thread-composer')).toBeNull();
  });

  it('closes a resolved thread to everyone and says so', () => {
    render(
      <ThreadView
        thread={{ ...baseThread, resolved_at: '2026-09-16T09:00:00Z', can_resolve: true }}
        onPost={vi.fn()}
        onResolve={vi.fn()}
      />,
    );
    expect(screen.getByTestId('thread-resolved-notice')).toHaveTextContent('closed');
    expect(screen.queryByTestId('thread-composer')).toBeNull();
    expect(screen.queryByTestId('thread-resolve')).toBeNull();
  });

  it('offers resolve only when the viewer may resolve', async () => {
    const onResolve = vi.fn();
    render(
      <ThreadView thread={{ ...baseThread, can_resolve: true }} onPost={vi.fn()} onResolve={onResolve} />,
    );
    await userEvent.click(screen.getByTestId('thread-resolve'));
    expect(onResolve).toHaveBeenCalled();
  });
});
