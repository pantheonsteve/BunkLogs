import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import CamperCareRequestFormPage from '../CamperCareRequestFormPage';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

function PathProbe() {
  const loc = useLocation();
  return <div data-testid="path-probe" data-pathname={loc.pathname} />;
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/counselor/requests/camper-care/new']}>
      <Routes>
        <Route
          path="/counselor/requests/camper-care/new"
          element={<CamperCareRequestFormPage />}
        />
        <Route path="/counselor" element={<PathProbe />} />
        <Route path="/counselor" element={<PathProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

const rosterPayload = {
  date: '2026-07-04',
  editable: true,
  template: { id: 9, slug: 'camper', name: 'Camper', version: 1 },
  bunks: [
    {
      id: 1,
      slug: 'pine',
      name: 'Pine',
      covered: 0,
      total: 2,
      campers: [
        { id: 100, name: 'Avi L', preferred_name: 'Avi', first_name: 'Avi', last_initial: 'L', submitted: false, reflection_id: null, submitter: null, editable: false },
        { id: 101, name: 'Beth M', preferred_name: 'Beth', first_name: 'Beth', last_initial: 'M', submitted: false, reflection_id: null, submitter: null, editable: false },
      ],
      off_camp: [
        { id: 102, name: 'Carl N', preferred_name: 'Carl', first_name: 'Carl', last_initial: 'N' },
      ],
    },
    {
      id: 2,
      slug: 'oak',
      name: 'Oak',
      covered: 0,
      total: 1,
      campers: [
        { id: 200, name: 'Dana O', preferred_name: 'Dana', first_name: 'Dana', last_initial: 'O', submitted: false, reflection_id: null, submitter: null, editable: false },
      ],
      off_camp: [],
    },
  ],
};

const suggestionPayload = {
  suggestions: [
    { id: 'sug-1', label: 'Toothpaste', sort_order: 1 },
    { id: 'sug-2', label: 'Sunscreen', sort_order: 2 },
  ],
};

describe('CamperCareRequestFormPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  function arrange(suggestions = suggestionPayload) {
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/counselor/camper-reflections/') {
        return Promise.resolve({ data: rosterPayload });
      }
      if (url === '/api/v1/counselor/camper-care-item-suggestions/') {
        return Promise.resolve({ data: suggestions });
      }
      return Promise.reject(new Error(`Unmocked: ${url}`));
    });
  }

  it('flattens the roster across bunks (including off-camp) into the picker', async () => {
    arrange();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    const options = Array.from(
      screen.getByTestId('camper-care-subject').querySelectorAll('option'),
    );
    const labels = options.map((o) => o.textContent);
    // Empty option + Avi/Beth/Carl in Pine + Dana in Oak. Alphabetical
    // by bunk then by name; Pine comes before Oak in alpha, no — Oak
    // < Pine. So Oak's Dana first.
    expect(labels[0]).toMatch(/— bunk-wide/);
    expect(labels.slice(1)).toEqual([
      'Dana O (Oak)',
      'Avi L (Pine)',
      'Beth M (Pine)',
      'Carl N (Pine)',
    ]);
  });

  it('renders a datalist with the curated suggestions', async () => {
    arrange();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    const dl = document.getElementById('camper-care-item-options');
    expect(dl).toBeTruthy();
    const values = Array.from(dl.querySelectorAll('option')).map((o) => o.value);
    expect(values).toEqual(['Toothpaste', 'Sunscreen']);
  });

  it('skips the datalist when no suggestions exist (free text only)', async () => {
    arrange({ suggestions: [] });
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    expect(document.getElementById('camper-care-item-options')).toBeNull();
    expect(screen.getByTestId('camper-care-item').hasAttribute('list')).toBe(false);
  });

  it('survives a suggestions endpoint error gracefully', async () => {
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/counselor/camper-reflections/') {
        return Promise.resolve({ data: rosterPayload });
      }
      return Promise.reject(new Error('boom'));
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    expect(document.getElementById('camper-care-item-options')).toBeNull();
  });

  it('requires an item before submit', async () => {
    arrange();
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    // userEvent honors the `required` attr; remove it so we can test our
    // own validation message.
    const input = screen.getByTestId('camper-care-item');
    input.removeAttribute('required');
    await user.click(screen.getByTestId('camper-care-submit'));
    expect(postMock).not.toHaveBeenCalled();
  });

  it('POSTs with stable client_submission_id and routes to the list', async () => {
    arrange();
    postMock.mockResolvedValue({ data: { id: 'order-1' }, status: 201 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );

    await user.selectOptions(screen.getByTestId('camper-care-subject'), '100');
    await user.type(screen.getByTestId('camper-care-item'), 'Toothpaste');
    await user.type(screen.getByTestId('camper-care-item-note'), 'mint please');
    await user.type(screen.getByTestId('camper-care-description'), 'whole bunk is out');
    await user.click(screen.getByTestId('camper-care-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const [url, body] = postMock.mock.calls[0];
    expect(url).toBe('/api/v1/counselor/camper-care-requests/');
    expect(body.subject_id).toBe(100);
    expect(body.item).toBe('Toothpaste');
    expect(body.item_note).toBe('mint please');
    expect(body.description).toBe('whole bunk is out');
    expect(typeof body.client_submission_id).toBe('string');
    expect(body.client_submission_id.length).toBeGreaterThan(20);

    await waitFor(() =>
      expect(screen.getByTestId('path-probe')).toHaveAttribute(
        'data-pathname',
        '/counselor',
      ),
    );
  });

  it('omits subject_id for bunk-scoped requests', async () => {
    arrange();
    postMock.mockResolvedValue({ data: { id: 'order-2' }, status: 201 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );

    await user.type(screen.getByTestId('camper-care-item'), 'Bug spray');
    await user.click(screen.getByTestId('camper-care-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const body = postMock.mock.calls[0][1];
    expect(body).not.toHaveProperty('subject_id');
  });

  it('shows a 403 server message verbatim', async () => {
    arrange();
    postMock.mockRejectedValue({
      response: { status: 403, data: { detail: 'Camper is not on any of your bunks.' } },
    });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );

    await user.type(screen.getByTestId('camper-care-item'), 'X');
    await user.click(screen.getByTestId('camper-care-submit'));
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-submit-error')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('camper-care-submit-error')).toHaveTextContent(
      'Camper is not on any of your bunks.',
    );
  });

  it('surfaces 400 field errors per-field', async () => {
    arrange();
    postMock.mockRejectedValue({
      response: { status: 400, data: { item: ['This field is required.'] } },
    });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-form')).toBeInTheDocument(),
    );
    await user.type(screen.getByTestId('camper-care-item'), 'X');
    await user.click(screen.getByTestId('camper-care-submit'));
    await waitFor(() =>
      expect(screen.getByTestId('camper-care-submit-error')).toBeInTheDocument(),
    );
    expect(screen.getByText('This field is required.')).toBeInTheDocument();
  });
});
