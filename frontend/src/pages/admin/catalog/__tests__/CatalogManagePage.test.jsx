import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CatalogManagePage from '../CatalogManagePage';

const fetchCatalogTree = vi.fn();
const createCatalogStore = vi.fn();

vi.mock('../../../../api/admin', () => ({
  fetchCatalogTree: (...a) => fetchCatalogTree(...a),
  createCatalogStore: (...a) => createCatalogStore(...a),
  patchCatalogStore: vi.fn(),
  deleteCatalogStore: vi.fn(),
  createCatalogRequestType: vi.fn(),
  patchCatalogRequestType: vi.fn(),
  deleteCatalogRequestType: vi.fn(),
  createCatalogItem: vi.fn(),
  patchCatalogItem: vi.fn(),
  deleteCatalogItem: vi.fn(),
  importCatalogCsv: vi.fn(),
  downloadCatalogTemplate: vi.fn(),
}));

const TREE = {
  stores: [
    {
      id: 1,
      name: 'Camper Care',
      fulfilling_role: 'camper_care',
      is_active: true,
      request_types: [
        {
          id: 10,
          name: 'Camper Care Items Request',
          is_active: true,
          items: [
            { id: 100, name: 'Toothbrush', track_quantity: true, unit: '', is_active: true },
          ],
        },
      ],
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/catalog']}>
      <CatalogManagePage />
    </MemoryRouter>,
  );
}

describe('CatalogManagePage', () => {
  beforeEach(() => {
    fetchCatalogTree.mockReset();
    createCatalogStore.mockReset();
    fetchCatalogTree.mockResolvedValue(TREE);
  });

  it('renders the store / request type / item tree', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('store-1')).toBeInTheDocument());
    expect(screen.getByText('Camper Care Items Request')).toBeInTheDocument();
    expect(screen.getByText('Toothbrush')).toBeInTheDocument();
  });

  it('creates a new store via the modal', async () => {
    createCatalogStore.mockResolvedValue({ id: 2 });
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId('catalog-add-store'));

    await user.click(screen.getByTestId('catalog-add-store'));
    await user.type(screen.getByTestId('store-name'), 'Maintenance');
    await user.click(screen.getByTestId('store-submit'));

    await waitFor(() => expect(createCatalogStore).toHaveBeenCalled());
    expect(createCatalogStore.mock.calls[0][0]).toMatchObject({ name: 'Maintenance' });
  });

  it('shows an empty state when there are no stores', async () => {
    fetchCatalogTree.mockResolvedValue({ stores: [] });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('catalog-empty')).toBeInTheDocument());
  });

  it('filters the tree by the search box', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Toothbrush')).toBeInTheDocument());

    await user.type(screen.getByTestId('catalog-search'), 'zzz');
    await waitFor(() => expect(screen.getByTestId('catalog-no-matches')).toBeInTheDocument());
    expect(screen.queryByText('Toothbrush')).not.toBeInTheDocument();

    await user.clear(screen.getByTestId('catalog-search'));
    await user.type(screen.getByTestId('catalog-search'), 'tooth');
    await waitFor(() => expect(screen.getByText('Toothbrush')).toBeInTheDocument());
  });
});
