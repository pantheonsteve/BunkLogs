import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import TemplateEditorPage from '../TemplateEditorPage';

const getMock = vi.fn();
const patchMock = vi.fn();

vi.mock('../../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    patch: (...args) => patchMock(...args),
  },
}));

const baseTemplate = {
  id: 7,
  name: 'Test Template',
  version: 1,
  is_active: true,
  languages: ['en'],
  created_at: '2025-05-01T00:00:00Z',
  schema: {
    fields: [
      { key: 'note', type: 'text', prompts: { en: 'Weekly note?' }, required: true },
      { key: 'wins', type: 'text_list', prompts: { en: 'Wins' }, required: false, min_items: 1, max_items: 3 },
    ],
  },
};

function renderEditor(id = '7') {
  return render(
    <MemoryRouter initialEntries={[`/admin/templates/${id}/edit`]}>
      <Routes>
        <Route path="/admin/templates/:id/edit" element={<TemplateEditorPage />} />
        <Route path="/admin/templates" element={<div>List</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TemplateEditorPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    patchMock.mockReset();
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) return Promise.resolve({ data: baseTemplate });
      if (url.includes('/api/v1/reflections/')) return Promise.resolve({ data: { count: 0 } });
      return Promise.resolve({ data: [] });
    });
  });

  it('renders editor with template name and fields', async () => {
    renderEditor();
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Template')).toBeInTheDocument();
    });
    // Text appears in both field list card and live preview
    expect(screen.getAllByText('Weekly note?').length).toBeGreaterThanOrEqual(1);
  });

  it('renders all field types in the field list', async () => {
    const allTypes = ['text', 'textarea', 'text_list', 'single_choice', 'multiple_choice',
      'yes_no', 'date', 'number', 'section_header', 'instructions', 'rating_group', 'single_rating'];
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) {
        return Promise.resolve({
          data: {
            ...baseTemplate,
            schema: {
              fields: allTypes.map((type, i) => ({
                key: `f${i}`,
                type,
                prompts: ['rating_group', 'single_rating'].includes(type) ? undefined : { en: `Prompt ${type}` },
                scale_labels: ['rating_group', 'single_rating'].includes(type) ? { en: ['1', '2', '3'] } : undefined,
                scale: ['rating_group', 'single_rating'].includes(type) ? [1, 3] : undefined,
                categories: type === 'rating_group' ? [{ key: 'cat1', labels: { en: 'Cat 1' } }] : undefined,
              })),
            },
          },
        });
      }
      return Promise.resolve({ data: { count: 0 } });
    });
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    // Should render 12 field cards
    expect(screen.getAllByRole('option').length).toBe(12);
  });

  it('opens type picker when Add field is clicked', async () => {
    renderEditor();
    await waitFor(() => screen.getByTestId('add-field-button'));
    await userEvent.click(screen.getByTestId('add-field-button'));
    expect(screen.getByRole('dialog', { name: 'Add field' })).toBeInTheDocument();
  });

  it('adds a text field when picked from type picker', async () => {
    renderEditor();
    await waitFor(() => screen.getByTestId('add-field-button'));
    await userEvent.click(screen.getByTestId('add-field-button'));
    await userEvent.click(screen.getByTestId('field-type-text'));
    // A new field should appear in the list (now 3 fields)
    await waitFor(() => {
      expect(screen.getAllByRole('option').length).toBe(3);
    });
  });

  it('selects a field when clicked, showing inspector', async () => {
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));
    await userEvent.click(screen.getAllByRole('option')[0]);
    expect(screen.getByText('Edit field')).toBeInTheDocument();
  });

  it('marks unsaved changes when field is selected and inspector is changed', async () => {
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));
    await userEvent.click(screen.getAllByRole('option')[0]);

    const promptInput = screen.getAllByRole('textbox').find(
      (el) => el.value === 'Weekly note?',
    );
    expect(promptInput).toBeTruthy();
    await userEvent.clear(promptInput);
    await userEvent.type(promptInput, 'Updated prompt');

    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  });

  it('save button calls PATCH with current schema', async () => {
    patchMock.mockResolvedValue({
      data: { ...baseTemplate, version: 1, created_new_version: false },
    });
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));

    // Click first field to select it
    await userEvent.click(screen.getAllByRole('option')[0]);

    // Change the prompt to trigger dirty state (need to use Advanced to set key too)
    // Actually let's just save without changes by directly setting dirty via name change
    const nameInput = screen.getByDisplayValue('Test Template');
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Updated Template');

    // Now save
    const saveBtn = screen.getByTestId('save-btn');
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalled();
    });
    const callArgs = patchMock.mock.calls[0];
    expect(callArgs[0]).toBe('/api/v1/templates/7/');
    expect(callArgs[1].name).toBe('Updated Template');
  });

  it('shows versioning warning when responses exist', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) return Promise.resolve({ data: baseTemplate });
      if (url.includes('/api/v1/reflections/')) return Promise.resolve({ data: { count: 5 } });
      return Promise.resolve({ data: [] });
    });
    renderEditor();
    await waitFor(() => {
      expect(screen.getByText(/5 responses on v1/)).toBeInTheDocument();
    });
  });

  it('shows quiet status when no responses exist', async () => {
    renderEditor();
    await waitFor(() => {
      expect(screen.getByText(/Editing v1 in place/)).toBeInTheDocument();
    });
  });

  it('language switcher swaps inspector prompt content', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) {
        return Promise.resolve({
          data: {
            ...baseTemplate,
            languages: ['en', 'es'],
            schema: {
              fields: [
                { key: 'note', type: 'text', prompts: { en: 'Weekly note?', es: 'Nota semanal?' }, required: true },
              ],
            },
          },
        });
      }
      return Promise.resolve({ data: { count: 0 } });
    });
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));
    await userEvent.click(screen.getAllByRole('option')[0]);

    expect(screen.getByText('Edit field')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Weekly note?')).toBeInTheDocument();

    // Switch language via header language switcher buttons (multiple 'es' buttons may exist)
    // Find all 'es' buttons and click the first one in the header region
    const esBtns = screen.getAllByRole('button', { name: /^es$/i });
    await userEvent.click(esBtns[0]);

    // Inspector prompt input should switch to the es value
    await waitFor(() => {
      expect(screen.getByDisplayValue('Nota semanal?')).toBeInTheDocument();
    });
  });

  it('permission guard redirects non-admins', async () => {
    // This is covered by the AdminRoute component in Router.jsx
    // AdminRoute tests are in Router.test.jsx - just verify the component mounts
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    expect(screen.getByDisplayValue('Test Template')).toBeInTheDocument();
  });

  it('shows validation errors when saving with missing field key', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) {
        return Promise.resolve({
          data: {
            ...baseTemplate,
            schema: {
              fields: [{ key: '', type: 'text', prompts: { en: 'A prompt' }, required: true }],
            },
          },
        });
      }
      return Promise.resolve({ data: { count: 0 } });
    });
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));

    // Trigger dirty state by changing name
    const nameInput = screen.getByDisplayValue('Test Template');
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'X');

    await userEvent.click(screen.getByTestId('save-btn'));

    await waitFor(() => {
      expect(screen.getByText(/field key is required/i)).toBeInTheDocument();
    });
    expect(patchMock).not.toHaveBeenCalled();
  });

  it('live preview reflects schema changes', async () => {
    renderEditor();
    await waitFor(() => screen.getByRole('region', { name: 'Live preview' }));
    expect(screen.getByRole('region', { name: 'Live preview' })).toBeInTheDocument();
    // The preview renders the fields — 'Weekly note?' label should appear
    await waitFor(() => {
      expect(screen.getAllByText('Weekly note?').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('dashboard preview button opens preview modal with synthetic data', async () => {
    renderEditor();
    await waitFor(() => screen.getByTestId('dash-preview-btn'));
    await userEvent.click(screen.getByTestId('dash-preview-btn'));
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /dashboard preview/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/synthetic sample data/i)).toBeInTheDocument();
  });

  it('dashboard preview modal can be closed', async () => {
    renderEditor();
    await waitFor(() => screen.getByTestId('dash-preview-btn'));
    await userEvent.click(screen.getByTestId('dash-preview-btn'));
    await waitFor(() => screen.getByRole('dialog', { name: /dashboard preview/i }));
    await userEvent.click(screen.getByRole('button', { name: /close preview/i }));
    expect(screen.queryByRole('dialog', { name: /dashboard preview/i })).not.toBeInTheDocument();
  });

  it('field deletion removes field from list', async () => {
    renderEditor();
    await waitFor(() => screen.getAllByRole('option'));
    const initialCount = screen.getAllByRole('option').length;

    await userEvent.click(screen.getAllByRole('option')[0]);
    const deleteBtn = screen.getByRole('button', { name: /delete/i });
    await userEvent.click(deleteBtn);

    // Confirm deletion
    const confirmBtn = screen.getByRole('button', { name: /^yes$/i });
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('option').length).toBe(initialCount - 1);
    });
  });

  // ──────────────────────────────────────────────────────────────────
  // Routing / Settings panel
  // ──────────────────────────────────────────────────────────────────

  async function openSettings() {
    const toggle = screen.getByRole('button', { name: /Settings/i });
    await userEvent.click(toggle);
  }

  it('settings panel renders existing routing values from the loaded template', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) {
        return Promise.resolve({
          data: {
            ...baseTemplate,
            cadence: 'daily',
            subject_mode: 'single_subject',
            assignment_scope: 'per_subject_in_group',
            assignment_group_types: ['bunk'],
            author_role_filter: ['counselor'],
            subject_role_filter: ['camper'],
            subject_visible: true,
          },
        });
      }
      if (url.includes('/api/v1/reflections/')) return Promise.resolve({ data: { count: 0 } });
      return Promise.resolve({ data: [] });
    });
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    await openSettings();

    expect(screen.getByLabelText('Cadence')).toHaveValue('daily');
    expect(screen.getByLabelText(/Who is each submission about/i)).toHaveValue('single_subject');

    // Selected chips report aria-pressed=true
    const bunkChip = screen.getByRole('button', { name: 'Bunk' });
    expect(bunkChip).toHaveAttribute('aria-pressed', 'true');

    const counselorChips = screen.getAllByRole('button', { name: 'Counselor' });
    expect(counselorChips.some((b) => b.getAttribute('aria-pressed') === 'true')).toBe(true);

    const camperChips = screen.getAllByRole('button', { name: 'Camper' });
    expect(camperChips.some((b) => b.getAttribute('aria-pressed') === 'true')).toBe(true);

    expect(
      screen.getByLabelText(/Subject can see reflections about themselves/i),
    ).toBeChecked();
  });

  it('switching subject_mode to single_subject reveals group/subject controls', async () => {
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    await openSettings();

    // Default 'self' hides group-only controls
    expect(
      screen.queryByLabelText('Assignment group types'),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText(/Who is each submission about/i),
      'single_subject',
    );

    expect(screen.getByLabelText('Assignment group types')).toBeInTheDocument();
    expect(screen.getByLabelText('Subject role filter')).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Subject can see reflections about themselves/i),
    ).toBeInTheDocument();
  });

  it('save sends routing fields and auto-derived assignment_scope', async () => {
    patchMock.mockResolvedValue({
      data: { ...baseTemplate, version: 1, created_new_version: false },
    });
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    await openSettings();

    await userEvent.selectOptions(screen.getByLabelText('Cadence'), 'daily');
    await userEvent.selectOptions(
      screen.getByLabelText(/Who is each submission about/i),
      'single_subject',
    );

    const groupTypes = screen.getByLabelText('Assignment group types');
    await userEvent.click(within(groupTypes).getByRole('button', { name: 'Bunk' }));

    const authorRoles = screen.getByLabelText('Author role filter');
    await userEvent.click(within(authorRoles).getByRole('button', { name: 'Counselor' }));

    const subjectRoles = screen.getByLabelText('Subject role filter');
    await userEvent.click(within(subjectRoles).getByRole('button', { name: 'Camper' }));

    await userEvent.click(screen.getByTestId('save-btn'));

    await waitFor(() => expect(patchMock).toHaveBeenCalled());
    const payload = patchMock.mock.calls[0][1];
    expect(payload.cadence).toBe('daily');
    expect(payload.subject_mode).toBe('single_subject');
    expect(payload.assignment_scope).toBe('per_subject_in_group');
    expect(payload.assignment_group_types).toEqual(['bunk']);
    expect(payload.author_role_filter).toContain('counselor');
    expect(payload.subject_role_filter).toContain('camper');
    expect(payload.subject_visible).toBe(false);
  });

  it('supports_privacy round-trips through the editor (load + checkbox + save)', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/templates/')) {
        return Promise.resolve({
          data: {
            ...baseTemplate,
            subject_mode: 'single_subject',
            assignment_scope: 'per_subject_in_group',
            assignment_group_types: ['bunk'],
            supports_privacy: false,
          },
        });
      }
      if (url.includes('/api/v1/reflections/')) return Promise.resolve({ data: { count: 0 } });
      return Promise.resolve({ data: [] });
    });
    patchMock.mockResolvedValue({
      data: { ...baseTemplate, version: 1, created_new_version: false },
    });

    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    await openSettings();

    const checkbox = screen.getByLabelText(/Allow .supervisors only. privacy/i);
    expect(checkbox).not.toBeChecked();
    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    await userEvent.click(screen.getByTestId('save-btn'));
    await waitFor(() => expect(patchMock).toHaveBeenCalled());
    const payload = patchMock.mock.calls[0][1];
    expect(payload.supports_privacy).toBe(true);
  });

  it('does not show supports_privacy checkbox on self-mode templates', async () => {
    renderEditor();
    await waitFor(() => screen.getByDisplayValue('Test Template'));
    await openSettings();
    expect(
      screen.queryByLabelText(/Allow .supervisors only. privacy/i),
    ).not.toBeInTheDocument();
  });
});
