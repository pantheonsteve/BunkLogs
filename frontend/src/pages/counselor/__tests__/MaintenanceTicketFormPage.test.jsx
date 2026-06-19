import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import MaintenanceTicketFormPage from '../MaintenanceTicketFormPage';

const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    post: (...args) => postMock(...args),
  },
}));

function PathProbe() {
  const loc = useLocation();
  return <div data-testid="path-probe" data-pathname={loc.pathname} />;
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/counselor/requests/maintenance/new']}>
      <Routes>
        <Route
          path="/counselor/requests/maintenance/new"
          element={<MaintenanceTicketFormPage />}
        />
        <Route path="/counselor" element={<PathProbe />} />
        <Route path="/counselor" element={<PathProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

// jsdom's URL doesn't ship createObjectURL out of the box.
beforeEach(() => {
  if (!URL.createObjectURL) {
    URL.createObjectURL = vi.fn(() => 'blob:mocked');
  } else {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mocked');
  }
  if (!URL.revokeObjectURL) {
    URL.revokeObjectURL = vi.fn();
  } else {
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  }
});

describe('MaintenanceTicketFormPage', () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it('renders the category options and defaults urgency to normal', () => {
    renderPage();
    const categoryOptions = Array.from(
      screen.getByTestId('maintenance-category').querySelectorAll('option'),
    ).map((o) => o.value);
    expect(categoryOptions).toEqual([
      '', 'plumbing', 'broken_light', 'pest', 'leak', 'other',
    ]);
    expect(screen.getByTestId('maintenance-urgency-normal')).toBeChecked();
    expect(screen.getByTestId('maintenance-urgency-urgent')).not.toBeChecked();
    // Urgent reason field is hidden initially.
    expect(screen.queryByTestId('maintenance-urgent-reason')).toBeNull();
  });

  it('reveals the urgent_reason textarea when urgency flips to urgent', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId('maintenance-urgency-urgent'));
    expect(screen.getByTestId('maintenance-urgent-reason')).toBeInTheDocument();
  });

  it('blocks submit when urgent_reason missing on an urgent ticket', async () => {
    const user = userEvent.setup();
    renderPage();
    // Bypass HTML `required` so we can hit our own validation path.
    screen.getByTestId('maintenance-location').removeAttribute('required');
    screen.getByTestId('maintenance-category').removeAttribute('required');

    await user.type(screen.getByTestId('maintenance-location'), 'Bunk Pine');
    await user.selectOptions(screen.getByTestId('maintenance-category'), 'leak');
    await user.click(screen.getByTestId('maintenance-urgency-urgent'));
    await user.click(screen.getByTestId('maintenance-submit'));

    expect(postMock).not.toHaveBeenCalled();
    expect(screen.getByText('Required when this is urgent.')).toBeInTheDocument();
  });

  it('attaches photos and previews them with remove affordance', async () => {
    const user = userEvent.setup();
    renderPage();
    const file = new File(['data'], 'shower.jpg', { type: 'image/jpeg' });
    const input = screen.getByTestId('maintenance-photo-input');
    await user.upload(input, file);

    expect(screen.getAllByTestId('maintenance-photo-tile')).toHaveLength(1);
    await user.click(screen.getByTestId('maintenance-photo-remove'));
    expect(screen.queryByTestId('maintenance-photo-tile')).toBeNull();
  });

  it('POSTs multipart with photos + urgent_reason and routes to the list', async () => {
    postMock.mockResolvedValue({ data: { id: 'mt-1' }, status: 201 });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByTestId('maintenance-location'), 'Bunk Pine');
    await user.selectOptions(screen.getByTestId('maintenance-category'), 'leak');
    await user.click(screen.getByTestId('maintenance-urgency-urgent'));
    await user.type(screen.getByTestId('maintenance-urgent-reason'), 'flooding');
    await user.type(screen.getByTestId('maintenance-description'), 'under sink');

    const file1 = new File(['x'], 'p1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['y'], 'p2.jpg', { type: 'image/jpeg' });
    await user.upload(screen.getByTestId('maintenance-photo-input'), [file1, file2]);

    await user.click(screen.getByTestId('maintenance-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const [url, body, config] = postMock.mock.calls[0];
    expect(url).toBe('/api/v1/counselor/maintenance-tickets/');
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('location')).toBe('Bunk Pine');
    expect(body.get('category')).toBe('leak');
    expect(body.get('urgency')).toBe('urgent');
    expect(body.get('urgent_reason')).toBe('flooding');
    expect(body.get('description')).toBe('under sink');
    expect(body.getAll('photos')).toHaveLength(2);
    expect(typeof body.get('client_submission_id')).toBe('string');
    expect(config).toEqual({ headers: { 'Content-Type': undefined } });

    await waitFor(() =>
      expect(screen.getByTestId('path-probe')).toHaveAttribute(
        'data-pathname',
        '/counselor',
      ),
    );
  });

  it('surfaces a 400 field error from the server', async () => {
    postMock.mockRejectedValue({
      response: { status: 400, data: { urgent_reason: ['Required when urgency is urgent.'] } },
    });
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByTestId('maintenance-location'), 'X');
    await user.selectOptions(screen.getByTestId('maintenance-category'), 'leak');
    await user.click(screen.getByTestId('maintenance-urgency-urgent'));
    await user.type(screen.getByTestId('maintenance-urgent-reason'), 'something');
    await user.click(screen.getByTestId('maintenance-submit'));
    await waitFor(() =>
      expect(screen.getByTestId('maintenance-submit-error')).toBeInTheDocument(),
    );
    expect(screen.getByText('Required when urgency is urgent.')).toBeInTheDocument();
  });
});
