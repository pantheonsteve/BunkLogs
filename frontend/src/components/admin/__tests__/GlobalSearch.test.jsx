import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../api/admin', () => ({
  searchAdmin: vi.fn(),
}));

import { searchAdmin } from '../../../api/admin';
import GlobalSearch from '../GlobalSearch';

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GlobalSearch (7_13 PR3, Story 60)', () => {
  it('renders results grouped by content type after debounce', async () => {
    searchAdmin.mockResolvedValue({
      query: 'ada',
      groups: {
        people: [
          { id: 1, label: 'Ada Lovelace', secondary: 'a@l.com', deep_link: '/profile/1' },
        ],
        notes: [],
      },
    });
    renderWithRouter(<GlobalSearch />);
    const input = screen.getByPlaceholderText(/Search campers/i);
    fireEvent.change(input, { target: { value: 'ada' } });

    // Wait for debounce + fetch to complete.
    await waitFor(() => expect(searchAdmin).toHaveBeenCalledWith('ada'), {
      timeout: 1000,
    });
    expect(await screen.findByTestId('global-search-group-people')).toBeInTheDocument();
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
  });

  it('does not call the API for queries shorter than 2 chars', async () => {
    renderWithRouter(<GlobalSearch />);
    const input = screen.getByPlaceholderText(/Search campers/i);
    fireEvent.change(input, { target: { value: 'a' } });
    // Give the debounce more than enough time.
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(searchAdmin).not.toHaveBeenCalled();
  });
});
