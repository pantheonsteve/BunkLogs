import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ConcernsInbox from '../ConcernsInbox';

const postMock = vi.fn();
const deleteMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    post: (...args) => postMock(...args),
    delete: (...args) => deleteMock(...args),
  },
}));

const payload = {
  period: { start: '2026-06-01', end: '2026-06-14' },
  include_read: false,
  items: [
    {
      reflection_id: 1,
      field_key: 'concerns',
      kind: 'open_concern',
      read: false,
      date: '2026-06-10',
      subject_id: 5,
      subject_name: 'Alex Kim',
      author_name: 'Sam Lee',
      template_name: 'Daily log',
      team_visibility: 'team',
      field_label: 'Concerns?',
      value: 'Homesick today',
    },
    {
      reflection_id: 2,
      field_key: 'overall',
      kind: 'low_rating',
      read: false,
      date: '2026-06-11',
      subject_id: 6,
      subject_name: 'Jordan Park',
      author_name: 'Sam Lee',
      template_name: 'Daily log',
      team_visibility: 'team',
      field_label: 'Overall',
      value: 1,
    },
  ],
};

beforeEach(() => {
  postMock.mockReset();
  deleteMock.mockReset();
  postMock.mockResolvedValue({ data: { updated: 2, read: true } });
});

describe('ConcernsInbox bulk actions', () => {
  it('selects all and bulk marks unread items as read', async () => {
    const user = userEvent.setup();
    const onChanged = vi.fn();
    render(
      <MemoryRouter>
        <ConcernsInbox payload={payload} onChanged={onChanged} />
      </MemoryRouter>,
    );

    await user.click(screen.getByTestId('concerns-select-all'));
    expect(screen.getByTestId('concerns-bulk-mark-read')).toHaveTextContent('Mark 2 as read');

    await user.click(screen.getByTestId('concerns-bulk-mark-read'));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/concerns/bulk-read/',
      {
        read: true,
        items: [
          { reflection_id: 1, field_key: 'concerns' },
          { reflection_id: 2, field_key: 'overall' },
        ],
      },
    ));
    expect(onChanged).toHaveBeenCalled();
  });
});
