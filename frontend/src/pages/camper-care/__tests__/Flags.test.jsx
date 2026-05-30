import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CamperCareFlags from '../Flags';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

const samplePayload = {
  today: '2026-07-04',
  items: [
    {
      id: '11111111-1111-1111-1111-111111111111',
      status: 'active',
      subject_camper: { id: 1, first_name: 'Lila', last_name: 'Park', preferred_name: '' },
      flagged_for_role: 'camper_care',
      trigger_content_type: 'note',
      trigger_content_id: 'abc-123',
      raised_by: { membership_id: 5, role: 'specialist', name: 'Rivka G.' },
      created_at: '2026-07-04T10:00:00Z',
      updated_at: '2026-07-04T10:00:00Z',
      resolved_at: null,
      is_today: true,
    },
    {
      id: '22222222-2222-2222-2222-222222222222',
      status: 'followed_up',
      subject_camper: { id: 2, first_name: 'Jordan', last_name: 'Tate', preferred_name: 'Jo' },
      flagged_for_role: 'camper_care',
      trigger_content_type: 'reflection',
      trigger_content_id: 'def-456',
      raised_by: { membership_id: 6, role: 'unit_head', name: 'Maya R.' },
      created_at: '2026-07-02T10:00:00Z',
      updated_at: '2026-07-03T10:00:00Z',
      resolved_at: null,
      is_today: false,
    },
  ],
};

describe('CamperCareFlags', () => {
  it('renders Today and Carried-over sections from the active+followed_up listing', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareFlags />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-flags')).toBeInTheDocument();
    });
    const todays = screen.getByTestId('cc-flags-today');
    expect(todays).toHaveTextContent(/Lila Park/);
    const carried = screen.getByTestId('cc-flags-carried');
    expect(carried).toHaveTextContent(/Jo Tate/);
  });

  it('resolves a flag with a required closing note and reloads', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    postMock.mockResolvedValueOnce({ data: { flag: {}, history: [] } });
    getMock.mockResolvedValueOnce({
      data: { ...samplePayload, items: [samplePayload.items[1]] },
    });

    render(
      <MemoryRouter>
        <CamperCareFlags />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('flag-row-11111111-1111-1111-1111-111111111111')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('flag-action-resolve-11111111-1111-1111-1111-111111111111'));
    expect(screen.getByTestId('flag-transition-modal')).toBeInTheDocument();

    // Submitting without a note should not call the API (HTML required attr).
    const submitBtn = screen.getByTestId('flag-transition-submit');
    await user.click(submitBtn);
    expect(postMock).not.toHaveBeenCalled();

    await user.type(screen.getByTestId('flag-transition-note'), 'Spoke with cabin; resolved.');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalled();
    });
    const [url, payload] = postMock.mock.calls[0];
    expect(url).toBe(
      '/api/v1/camper-care/flags/11111111-1111-1111-1111-111111111111/resolve/',
    );
    expect(payload.note).toBe('Spoke with cabin; resolved.');
  });

  it('links the camper name to the camper dashboard with anchored flag id and renders trigger_preview', async () => {
    const enriched = {
      ...samplePayload,
      items: [
        {
          ...samplePayload.items[0],
          trigger_content_type: 'specialist_note',
          trigger_preview: 'Camper had a hard night, started crying after lights-out and is asking for parent contact.',
        },
        samplePayload.items[1],
      ],
    };
    getMock.mockResolvedValueOnce({ data: enriched });
    render(
      <MemoryRouter>
        <CamperCareFlags />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-flags')).toBeInTheDocument();
    });
    const flagId = '11111111-1111-1111-1111-111111111111';
    const link = screen.getByTestId(`flag-camper-link-${flagId}`);
    expect(link).toHaveAttribute(
      'href',
      `/camper-care/campers/1?flagId=${encodeURIComponent(flagId)}#flag-${flagId}`,
    );
    const preview = screen.getByTestId(`flag-trigger-preview-${flagId}`);
    expect(preview).toHaveTextContent(/Camper had a hard night/);
    const sourceLabel = screen.getByText(/Source: Specialist note/);
    expect(sourceLabel).toBeInTheDocument();
  });

  it('expands a flag row to fetch and show the full note plus team activity', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    const flagId = '11111111-1111-1111-1111-111111111111';
    getMock.mockResolvedValueOnce({
      data: {
        flag: samplePayload.items[0],
        trigger: {
          content_type: 'specialist_note',
          body: 'Full note body with the entire account of what happened.',
          author: 'Rivka G.',
          created_at: '2026-07-04T10:00:00Z',
        },
        history: [
          {
            id: 'evt-1',
            event_type: 'state_changed',
            before_state: { status: 'active' },
            after_state: { status: 'followed_up' },
            reason_note: 'Checked in with the camper after dinner.',
            actor: { membership_id: 9, name: 'Morgan C.', role: 'camper_care' },
            created_at: '2026-07-04T12:00:00Z',
          },
        ],
      },
    });

    render(
      <MemoryRouter>
        <CamperCareFlags />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId(`flag-row-${flagId}`)).toBeInTheDocument();
    });

    await user.click(screen.getByTestId(`flag-expand-${flagId}`));

    await waitFor(() => {
      expect(screen.getByTestId(`flag-activity-${flagId}`)).toBeInTheDocument();
    });
    expect(getMock).toHaveBeenLastCalledWith(`/api/v1/camper-care/flags/${flagId}/`);
    const activity = screen.getByTestId(`flag-activity-${flagId}`);
    expect(activity).toHaveTextContent(/Full note body with the entire account/);
    expect(activity).toHaveTextContent(/Marked followed up/);
    expect(activity).toHaveTextContent(/Checked in with the camper after dinner/);
    expect(activity).toHaveTextContent(/Morgan C\./);
  });

  it('shows the resolved section when toggled and fetches with status=resolved', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    getMock.mockResolvedValueOnce({
      data: {
        today: samplePayload.today,
        items: [
          {
            ...samplePayload.items[0],
            id: '33333333-3333-3333-3333-333333333333',
            status: 'resolved',
          },
        ],
      },
    });
    render(
      <MemoryRouter>
        <CamperCareFlags />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-flags')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('cc-flags-resolved-toggle'));
    await waitFor(() => {
      const calls = getMock.mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[0]).toBe('/api/v1/camper-care/flags/');
      expect(lastCall[1]?.params?.status).toBe('resolved');
    });
    await waitFor(() => {
      expect(screen.getByTestId('flag-row-33333333-3333-3333-3333-333333333333')).toBeInTheDocument();
    });
  });
});
