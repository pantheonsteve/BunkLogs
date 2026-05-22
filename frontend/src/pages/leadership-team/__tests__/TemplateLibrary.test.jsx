import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TemplateLibrary from '../TemplateLibrary';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

beforeEach(() => {
  getMock.mockReset();
});

function renderLib() {
  return render(
    <MemoryRouter initialEntries={['/leadership-team/templates']}>
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
});
