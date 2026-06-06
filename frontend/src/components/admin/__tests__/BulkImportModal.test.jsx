import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../api/admin', () => ({
  previewAdminPeopleImport: vi.fn(),
  commitAdminPeopleImport: vi.fn(),
  listAdminPeopleImportTemplates: vi.fn(),
  downloadAdminPeopleImportTemplate: vi.fn(),
}));

import {
  previewAdminPeopleImport,
  commitAdminPeopleImport,
  listAdminPeopleImportTemplates,
  downloadAdminPeopleImportTemplate,
} from '../../../api/admin';
import BulkImportModal from '../BulkImportModal';

const PROGRAMS = [{ id: 1, slug: 'p1', name: 'Program 1' }];

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPeopleImportTemplates.mockResolvedValue({
    templates: [
      { variant: 'camper', label: 'Campers' },
      { variant: 'staff', label: 'Staff' },
    ],
  });
  downloadAdminPeopleImportTemplate.mockResolvedValue(undefined);
});

describe('BulkImportModal (7_13 PR3)', () => {
  it('preview then commit shows the import summary', async () => {
    previewAdminPeopleImport.mockResolvedValue({
      source: 'campminder',
      program: { id: 1, slug: 'p1' },
      summary: { row_count: 5, add: 2, change: 1, noop: 1, skip: 1, conflict: 0 },
      rows: [],
    });
    commitAdminPeopleImport.mockResolvedValue({
      status: 'completed',
      log: { id: 42, summary: { persons_created: 2, memberships_created: 3 } },
    });
    render(<BulkImportModal programs={PROGRAMS} onClose={() => {}} />);
    expect(screen.getByTestId('bulk-import-modal')).toBeInTheDocument();

    const fileInput = screen.getByTestId('bulk-import-file');
    const file = new File(['campminder_id\nC1'], 'test.csv', { type: 'text/csv' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByTestId('bulk-import-preview'));
    await waitFor(() => expect(previewAdminPeopleImport).toHaveBeenCalled());
    expect(await screen.findByTestId('bulk-import-preview-panel')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('bulk-import-commit'));
    await waitFor(() => expect(commitAdminPeopleImport).toHaveBeenCalled());
    expect(await screen.findByTestId('bulk-import-commit-panel')).toBeInTheDocument();
  });

  it('shows template download buttons for campminder imports', async () => {
    render(<BulkImportModal programs={PROGRAMS} onClose={() => {}} />);
    expect(await screen.findByTestId('bulk-import-template-staff')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('bulk-import-template-staff'));
    await waitFor(() => expect(downloadAdminPeopleImportTemplate).toHaveBeenCalledWith('campminder', 'staff'));
  });
});
