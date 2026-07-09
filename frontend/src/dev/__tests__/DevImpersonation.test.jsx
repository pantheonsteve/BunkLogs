import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DevImpersonation from '../DevImpersonation';

const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import api from '../../api';

function renderPanel() {
  return render(
    <MemoryRouter>
      <DevImpersonation />
    </MemoryRouter>,
  );
}

describe('DevImpersonation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    api.get.mockImplementation((url) => {
      if (url === '/api/dev/impersonate/status/') {
        return Promise.resolve({ data: { enabled: true } });
      }
      if (url === '/api/dev/impersonate/users/') {
        return Promise.resolve({
          data: {
            results: [
              {
                id: '1',
                email: 'counselor@test.com',
                first_name: 'Casey',
                last_name: 'Counselor',
                role: 'Counselor',
                membership_roles: [],
              },
            ],
          },
        });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });
    api.post.mockResolvedValue({
      data: {
        access: 'access-token',
        refresh: 'refresh-token',
        user: {
          id: '1',
          email: 'counselor@test.com',
          first_name: 'Casey',
          last_name: 'Counselor',
          role: 'Counselor',
          membership_roles: [],
        },
      },
    });
    mockLogin.mockResolvedValue({
      id: '1',
      email: 'counselor@test.com',
      first_name: 'Casey',
      last_name: 'Counselor',
      role: 'Counselor',
      membership_roles: [],
    });
  });

  it('impersonates a selected user and shows the banner', async () => {
    const user = userEvent.setup();
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId('dev-impersonation-toggle')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('dev-impersonation-toggle'));
    await waitFor(() => {
      expect(screen.getByText('Casey Counselor')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Casey Counselor'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        user: expect.objectContaining({ email: 'counselor@test.com' }),
      });
      expect(screen.getByTestId('dev-impersonation-banner')).toBeInTheDocument();
    });
  });
});
