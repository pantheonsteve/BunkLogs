import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();
const deleteMock = vi.fn();

vi.mock('../../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
    delete: (...args) => deleteMock(...args),
  },
}));

import FieldKeyListPage from '../FieldKeyListPage';

const KEYS = [
  {
    id: 1,
    organization: null,
    key: 'punctuality',
    display_name: 'Punctuality',
    description: 'Arrives on time.',
    expected_field_type: 'rating_group',
    expected_dashboard_role: 'category_ratings',
    is_global: true,
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    organization: 5,
    key: 'custom_metric',
    display_name: 'Custom Metric',
    description: '',
    expected_field_type: 'text',
    expected_dashboard_role: '',
    is_global: false,
    created_at: '2025-02-01T00:00:00Z',
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/field-keys']}>
      <FieldKeyListPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  deleteMock.mockReset();
  getMock.mockResolvedValue({ data: KEYS });
  vi.spyOn(window, 'confirm').mockReturnValue(true);
});

describe('FieldKeyListPage (3.29)', () => {
  it('lists field keys with scope chip and type label', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('fk-table')).toBeInTheDocument());

    const globalRow = screen.getByTestId('fk-row-punctuality');
    const orgRow = screen.getByTestId('fk-row-custom_metric');
    expect(within(globalRow).getByText('Global')).toBeInTheDocument();
    expect(within(orgRow).getByText('Org')).toBeInTheDocument();
    // type labels are humanized
    expect(within(globalRow).getByText('Rating group')).toBeInTheDocument();
    expect(within(orgRow).getByText('Short text')).toBeInTheDocument();
  });

  it('scope filter narrows rows to global and back to mine', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));

    await userEvent.click(screen.getByTestId('fk-scope-global'));
    expect(screen.getByTestId('fk-row-punctuality')).toBeInTheDocument();
    expect(screen.queryByTestId('fk-row-custom_metric')).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId('fk-scope-mine'));
    expect(screen.queryByTestId('fk-row-punctuality')).not.toBeInTheDocument();
    expect(screen.getByTestId('fk-row-custom_metric')).toBeInTheDocument();
  });

  it('search input drives ?q= on the API call', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));
    getMock.mockClear();

    await userEvent.type(screen.getByTestId('fk-search'), 'punc');
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith(
        '/api/v1/field-keys/',
        expect.objectContaining({ params: { q: 'punc' } }),
      );
    });
  });

  it('creates a new field key and refreshes the list', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));

    await userEvent.click(screen.getByTestId('fk-new-btn'));
    const form = await screen.findByTestId('fk-create-form');
    expect(form).toBeInTheDocument();

    await userEvent.type(screen.getByTestId('fk-form-key'), 'energy');
    await userEvent.type(screen.getByTestId('fk-form-display-name'), 'Energy');

    postMock.mockResolvedValueOnce({ data: { id: 99 } });
    getMock.mockResolvedValueOnce({
      data: [
        ...KEYS,
        {
          id: 99,
          organization: 5,
          key: 'energy',
          display_name: 'Energy',
          description: '',
          expected_field_type: '',
          expected_dashboard_role: '',
          is_global: false,
          created_at: '2025-03-01T00:00:00Z',
        },
      ],
    });

    await userEvent.click(screen.getByTestId('fk-create-submit'));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith(
        '/api/v1/field-keys/',
        expect.objectContaining({
          key: 'energy',
          display_name: 'Energy',
        }),
      );
    });
    await waitFor(() => expect(screen.getByTestId('fk-row-energy')).toBeInTheDocument());
  });

  it('removes a row on successful delete', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));

    deleteMock.mockResolvedValueOnce({ status: 204 });
    getMock.mockResolvedValueOnce({ data: [KEYS[0]] }); // custom_metric removed

    await userEvent.click(screen.getByTestId('fk-delete-custom_metric'));

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith('/api/v1/field-keys/2/');
    });
    await waitFor(() => {
      expect(screen.queryByTestId('fk-row-custom_metric')).not.toBeInTheDocument();
    });
  });

  it('keeps the row and shows toast when delete returns 409', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));

    deleteMock.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: 'Key "custom_metric" is referenced by one or more templates.' },
      },
    });

    await userEvent.click(screen.getByTestId('fk-delete-custom_metric'));

    await waitFor(() => {
      expect(screen.getByTestId('fk-toast')).toHaveTextContent(/referenced by one or more templates/i);
    });
    // row is still there
    expect(screen.getByTestId('fk-row-custom_metric')).toBeInTheDocument();
  });

  it('opens the edit modal, locks the key field, and patches on save', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('fk-table'));

    await userEvent.click(screen.getByTestId('fk-edit-custom_metric'));
    const submit = await screen.findByTestId('fk-edit-submit');
    expect(submit).toBeInTheDocument();

    // Key field should be read-only inside the modal
    const keyInputs = screen.getAllByTestId('fk-form-key');
    const modalKey = keyInputs[keyInputs.length - 1];
    expect(modalKey).toHaveAttribute('readonly');

    const nameInputs = screen.getAllByTestId('fk-form-display-name');
    const modalName = nameInputs[nameInputs.length - 1];
    await userEvent.clear(modalName);
    await userEvent.type(modalName, 'Custom Metric Renamed');

    patchMock.mockResolvedValueOnce({ data: {} });
    getMock.mockResolvedValueOnce({ data: KEYS });

    await userEvent.click(submit);

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith(
        '/api/v1/field-keys/2/',
        expect.objectContaining({ display_name: 'Custom Metric Renamed' }),
      );
    });
  });
});
