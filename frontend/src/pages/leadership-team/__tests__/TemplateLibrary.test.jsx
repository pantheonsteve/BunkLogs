import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import TemplateLibrary from '../TemplateLibrary';

const getMock = vi.fn();
const postMock = vi.fn();
const deleteMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: vi.fn(),
    delete: (...args) => deleteMock(...args),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  deleteMock.mockReset();
});

function renderLib() {
  return render(
    <MemoryRouter initialEntries={['/admin/templates']}>
      <TemplateLibrary />
    </MemoryRouter>,
  );
}

describe('LeadershipTeamTemplateLibrary', () => {
  it('renders templates from the {templates: [...]} response shape', async () => {
    // Backend (POST and GET on /api/v1/leadership-team/templates/) returns
    // `{ templates: [...] }`, NOT `{ results: [...] }`. Regression guard
    // for the silent-empty-list bug where the page rendered "no templates
    // match" right after a successful create.
    getMock.mockResolvedValue({
      data: {
        templates: [
          {
            id: 7,
            name: 'Kitchen Daily',
            status: 'draft',
            version: 1,
            role: 'kitchen_staff',
            languages: ['en'],
            cadence: 'daily',
          },
        ],
      },
    });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-row-7')).toBeInTheDocument());
    expect(screen.getByText('Kitchen Daily')).toBeInTheDocument();
    expect(screen.getByText(/draft v1/)).toBeInTheDocument();
  });

  it('shows the empty state when the org has no templates', async () => {
    getMock.mockResolvedValue({ data: { templates: [] } });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-empty')).toBeInTheDocument());
  });

  it('surfaces a 403 as a friendly error', async () => {
    getMock.mockRejectedValue({ response: { status: 403 } });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-error')).toBeInTheDocument());
    expect(screen.getByTestId('lt-tpl-error')).toHaveTextContent(/LT access/i);
  });

  it('shows active_assignment_count badge when present', async () => {
    getMock.mockResolvedValue({
      data: {
        templates: [
          {
            id: 9, name: 'Counselor Daily', status: 'published', version: 1,
            role: 'counselor', languages: ['en'], cadence: 'daily',
            active_assignment_count: 3,
          },
          {
            id: 10, name: 'Specialist Daily', status: 'published', version: 1,
            role: 'specialist', languages: ['en'], cadence: 'daily',
            active_assignment_count: 0,
          },
        ],
      },
    });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-row-9')).toBeInTheDocument());
    expect(screen.getByTestId('lt-tpl-assignments-9')).toHaveTextContent('3 active assignments');
    expect(screen.getByTestId('lt-tpl-assignments-10')).toHaveTextContent(/Not assigned/i);
    // Assign button only on published rows.
    expect(screen.getByTestId('lt-tpl-assign-9')).toBeInTheDocument();
  });

  it('shows Unpublish button for published templates and calls the API', async () => {
    getMock
      .mockResolvedValueOnce({
        data: {
          templates: [
            {
              id: 40, name: 'Live Template', status: 'published', version: 1,
              languages: ['en'], cadence: 'daily', reflection_count: 2,
            },
          ],
        },
      })
      .mockResolvedValue({ data: { templates: [] } });
    postMock.mockResolvedValue({ data: { id: 40, status: 'draft', is_active: false } });
    const user = userEvent.setup();

    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-unpublish-40')).toBeInTheDocument());

    // Delete hidden once responses exist
    expect(screen.queryByTestId('lt-tpl-delete-40')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('lt-tpl-unpublish-40'));
    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith(
        expect.stringContaining('/unpublish/'),
        expect.anything(),
        expect.anything(),
      ),
    );
  });

  it('links New template to /admin/templates/new', async () => {
    getMock.mockResolvedValue({ data: { templates: [] } });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-templates-new')).toBeInTheDocument());
    expect(screen.getByTestId('lt-templates-new')).toHaveAttribute('href', '/admin/templates/new');
  });

  it('links edit rows to /admin/templates/:id', async () => {
    getMock.mockResolvedValue({
      data: {
        templates: [
          { id: 11, name: 'Draft One', status: 'draft', version: 1, languages: ['en'], cadence: 'daily' },
        ],
      },
    });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-edit-11')).toBeInTheDocument());
    expect(screen.getByTestId('lt-tpl-edit-11')).toHaveAttribute('href', '/admin/templates/11');
  });

  it('shows an Edit button for every template', async () => {
    getMock.mockResolvedValue({
      data: {
        templates: [
          { id: 11, name: 'Draft One', status: 'draft', version: 1, languages: ['en'], cadence: 'daily' },
          { id: 12, name: 'Published One', status: 'published', version: 1, languages: ['en'], cadence: 'daily' },
        ],
      },
    });
    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-row-11')).toBeInTheDocument());
    expect(screen.getByTestId('lt-tpl-edit-11')).toBeInTheDocument();
    expect(screen.getByTestId('lt-tpl-edit-12')).toBeInTheDocument();
  });

  it('shows Delete when a template has no responses and requires confirmation', async () => {
    getMock
      .mockResolvedValueOnce({
        data: {
          templates: [
            {
              id: 20, name: 'Draft Template', status: 'draft', version: 1,
              languages: ['en'], cadence: 'daily', reflection_count: 0,
            },
            {
              id: 21, name: 'Published Template', status: 'published', version: 1,
              languages: ['en'], cadence: 'daily', reflection_count: 0,
            },
            {
              id: 22, name: 'Used Template', status: 'published', version: 1,
              languages: ['en'], cadence: 'daily', reflection_count: 3,
            },
          ],
        },
      })
      .mockResolvedValue({ data: { templates: [] } });
    deleteMock.mockResolvedValue({});
    const user = userEvent.setup();

    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-row-20')).toBeInTheDocument());

    expect(screen.getByTestId('lt-tpl-delete-20')).toBeInTheDocument();
    expect(screen.getByTestId('lt-tpl-delete-21')).toBeInTheDocument();
    expect(screen.queryByTestId('lt-tpl-delete-22')).not.toBeInTheDocument();

    // Click Delete shows confirmation
    await user.click(screen.getByTestId('lt-tpl-delete-20'));
    expect(screen.getByTestId('lt-tpl-delete-confirm-20')).toBeInTheDocument();
    expect(screen.getByTestId('lt-tpl-delete-cancel-20')).toBeInTheDocument();

    // Confirm deletion calls delete API
    await user.click(screen.getByTestId('lt-tpl-delete-confirm-20'));
    await waitFor(() => expect(deleteMock).toHaveBeenCalledOnce());
  });

  it('cancelling delete confirmation keeps the template row', async () => {
    getMock.mockResolvedValue({
      data: {
        templates: [
          { id: 30, name: 'Kept Draft', status: 'draft', version: 1, languages: ['en'], cadence: 'daily' },
        ],
      },
    });
    const user = userEvent.setup();

    renderLib();
    await waitFor(() => expect(screen.getByTestId('lt-tpl-delete-30')).toBeInTheDocument());
    await user.click(screen.getByTestId('lt-tpl-delete-30'));
    expect(screen.getByTestId('lt-tpl-delete-cancel-30')).toBeInTheDocument();

    await user.click(screen.getByTestId('lt-tpl-delete-cancel-30'));
    expect(screen.getByTestId('lt-tpl-delete-30')).toBeInTheDocument();
    expect(deleteMock).not.toHaveBeenCalled();
  });
});
