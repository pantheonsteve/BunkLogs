import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../api/admin', () => ({
  listAdminTemplates: vi.fn(),
  reviewAdminTemplate: vi.fn(),
}));

import { listAdminTemplates, reviewAdminTemplate } from '../../../api/admin';
import AdminTemplates from '../Templates';

const RESPONSE = {
  pending_review_count: 1,
  results: [
    { id: 1, name: 'Pending Template', slug: 'p', status: 'published',
      role: 'counselor', cadence: 'daily', languages: ['en'],
      pending_review: true, review_status: null },
    { id: 2, name: 'Reviewed Template', slug: 'r', status: 'published',
      role: 'counselor', cadence: 'daily', languages: ['en'],
      pending_review: false, review_status: 'reviewed' },
  ],
  grouped: {
    draft: [],
    published: [
      { id: 1, name: 'Pending Template', slug: 'p', status: 'published',
        role: 'counselor', cadence: 'daily', languages: ['en'],
        pending_review: true, review_status: null },
      { id: 2, name: 'Reviewed Template', slug: 'r', status: 'published',
        role: 'counselor', cadence: 'daily', languages: ['en'],
        pending_review: false, review_status: 'reviewed' },
    ],
    archived: [],
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  listAdminTemplates.mockResolvedValue(RESPONSE);
});

describe('AdminTemplates (7_13 PR3, Story 57)', () => {
  it('renders pending-review badge + reviewed pill', async () => {
    render(<AdminTemplates />);
    expect(await screen.findByTestId('templates-pending-summary')).toHaveTextContent(/1 pending/);
    expect(screen.getByTestId('template-pending-1')).toBeInTheDocument();
    expect(screen.queryByTestId('template-pending-2')).not.toBeInTheDocument();
  });

  it('posts a review with the entered note when Mark reviewed is clicked', async () => {
    reviewAdminTemplate.mockResolvedValue({ id: 1, review_status: 'reviewed', pending_review: false });
    render(<AdminTemplates />);
    await screen.findByTestId('template-row-1');
    fireEvent.click(screen.getByTestId('template-review-open-1'));
    const panel = await screen.findByTestId('template-review-panel-1');
    const noteInput = panel.querySelector('input');
    fireEvent.change(noteInput, { target: { value: 'all good' } });
    fireEvent.click(screen.getByTestId('template-mark-reviewed-1'));
    await waitFor(() =>
      expect(reviewAdminTemplate).toHaveBeenCalledWith(1, {
        review_status: 'reviewed', review_note: 'all good',
      }),
    );
  });
});
