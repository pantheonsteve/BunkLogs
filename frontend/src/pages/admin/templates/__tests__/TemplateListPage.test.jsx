import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import TemplateListPage from '../TemplateListPage';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

const TEMPLATES = [
  {
    id: 1,
    name: 'Weekly Counselor',
    role: 'counselor',
    version: 2,
    is_active: true,
    organization: 5,
    created_at: '2025-01-15T10:00:00Z',
  },
  {
    id: 2,
    name: 'Global Staff',
    role: 'general_counselor',
    version: 1,
    is_active: false,
    organization: null,
    created_at: '2025-01-10T10:00:00Z',
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/templates']}>
      <Routes>
        <Route path="/admin/templates" element={<TemplateListPage />} />
        <Route path="/admin/templates/:id/edit" element={<div>Editor</div>} />
        <Route path="/admin/templates/new" element={<div>New</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TemplateListPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    getMock.mockResolvedValue({ data: TEMPLATES });
  });

  it('renders template table with name and status', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('template-table')).toBeInTheDocument());
    expect(screen.getByText('Weekly Counselor')).toBeInTheDocument();
    expect(screen.getByText('Global Staff')).toBeInTheDocument();
    expect(screen.getByText('Published v2')).toBeInTheDocument();
    expect(screen.getByText('Archived')).toBeInTheDocument();
  });

  it('shows global label for templates without org', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('template-table'));
    expect(screen.getByText('global')).toBeInTheDocument();
  });

  it('filters by scope: mine vs global', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('template-table'));

    await userEvent.click(screen.getByRole('button', { name: /^Global$/i }));
    expect(screen.queryByText('Weekly Counselor')).not.toBeInTheDocument();
    expect(screen.getByText('Global Staff')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Mine$/i }));
    expect(screen.getByText('Weekly Counselor')).toBeInTheDocument();
    expect(screen.queryByText('Global Staff')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^All$/i }));
    expect(screen.getByText('Weekly Counselor')).toBeInTheDocument();
    expect(screen.getByText('Global Staff')).toBeInTheDocument();
  });

  it('renders new template button linking to /admin/templates/new', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('new-template-btn'));
    const btn = screen.getByTestId('new-template-btn');
    expect(btn).toHaveAttribute('href', '/admin/templates/new');
  });

  it('calls clone endpoint and reloads when Clone is clicked', async () => {
    postMock.mockResolvedValue({ data: { id: 99, name: 'Global Staff', version: 2 } });
    getMock
      .mockResolvedValueOnce({ data: TEMPLATES })
      .mockResolvedValueOnce({ data: TEMPLATES });
    renderPage();
    await waitFor(() => screen.getByTestId('template-table'));

    // Sorted by name asc: "Global Staff" (id=2) comes before "Weekly Counselor" (id=1)
    const cloneButtons = screen.getAllByRole('button', { name: /clone/i });
    await userEvent.click(cloneButtons[0]);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/templates/2/clone/');
    });
  });

  it('shows error message when load fails', async () => {
    getMock.mockRejectedValue({ response: { data: { detail: 'Server error' } } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument());
  });

  it('shows empty state with link to create when no templates', async () => {
    getMock.mockResolvedValue({ data: [] });
    renderPage();
    await waitFor(() => expect(screen.getByText('Create your first template')).toBeInTheDocument());
  });
});
