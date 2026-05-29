import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import TemplateBuilderPage from '../TemplateBuilder/TemplateBuilderPage';

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

vi.mock('../../../components/templates/ReflectionField', () => ({
  default: ({ field }) => (
    <div data-testid={`stub-field-${field.key || 'unset'}`}>{field.prompts?.en ?? ''}</div>
  ),
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
});

function renderNew() {
  return render(
    <MemoryRouter initialEntries={['/leadership-team/templates/new']}>
      <Routes>
        <Route path="/leadership-team/templates/new" element={<TemplateBuilderPage />} />
        <Route path="/leadership-team/templates/:id" element={<div data-testid="builder-redirect" />} />
      </Routes>
    </MemoryRouter>,
  );
}

/**
 * Render the builder in edit mode with a given template fixture.
 * getMock is pre-wired: first call returns the template, subsequent calls
 * (assignment list, groups) return empty arrays / objects.
 */
function renderEdit(templateFixture) {
  getMock.mockImplementation((url) => {
    if (url.includes('/templates/')) return Promise.resolve({ data: templateFixture });
    if (url.includes('/assignments/')) return Promise.resolve({ data: { assignments: [] } });
    if (url.includes('/assignment-groups/')) return Promise.resolve({ data: [] });
    return Promise.resolve({ data: {} });
  });
  return render(
    <MemoryRouter initialEntries={[`/leadership-team/templates/${templateFixture.id}`]}>
      <Routes>
        <Route path="/leadership-team/templates/:id" element={<TemplateBuilderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TemplateBuilderPage', () => {
  it('lets the LT user add a text field and post the new draft', async () => {
    postMock.mockResolvedValue({ data: { id: 99 } });
    renderNew();
    fireEvent.change(screen.getByTestId('lt-builder-name'), { target: { value: 'New LT template' } });
    fireEvent.click(screen.getByTestId('lt-builder-add-text'));
    const keyInput = await screen.findByText(/Prompt \(en\)/);
    expect(keyInput).toBeInTheDocument();
    // Fill the first added field
    const keyField = screen.getAllByPlaceholderText('field_key')[0];
    fireEvent.change(keyField, { target: { value: 'reflection_summary' } });
    const promptField = screen.getAllByRole('textbox').find(
      (el) => el !== keyField && el !== screen.getByTestId('lt-builder-name'),
    );
    fireEvent.change(promptField, { target: { value: 'How was your week?' } });
    fireEvent.click(screen.getByTestId('lt-builder-save'));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const body = postMock.mock.calls[0][1];
    expect(body.schema.fields[0].key).toBe('reflection_summary');
    expect(body.name).toBe('New LT template');
    // Slug must be derived client-side so the backend doesn't 400 on
    // missing slug (the LT builder UI never asks the user for one).
    expect(body.slug).toMatch(/^new-lt-template-[a-z0-9]+$/);
    // New fields are included in the payload with sane defaults.
    expect(body.subject_mode).toBe('self');
    expect(body.assignment_scope).toBe('none');
    expect(body.assignment_group_types).toEqual([]);
  });

  it('auto-syncs assignment_scope and shows group-type checkboxes when subject mode changes', async () => {
    postMock.mockResolvedValue({ data: { id: 99 } });
    renderNew();

    const modeSelect = screen.getByTestId('lt-builder-subject-mode');
    // Default: self → scope badge shows 'none' label; no group-type fieldset.
    expect(screen.getByTestId('lt-builder-assignment-scope')).toHaveTextContent('No group context');
    expect(screen.queryByTestId('lt-builder-group-types-fieldset')).not.toBeInTheDocument();

    // Switch to single_subject — scope becomes per_subject_in_group; fieldset appears.
    fireEvent.change(modeSelect, { target: { value: 'single_subject' } });
    expect(screen.getByTestId('lt-builder-assignment-scope')).toHaveTextContent('One reflection per subject in group');
    expect(screen.getByTestId('lt-builder-group-types-fieldset')).toBeInTheDocument();

    // Check a group type and save.
    fireEvent.click(screen.getByTestId('lt-builder-group-type-bunk'));
    fireEvent.change(screen.getByTestId('lt-builder-name'), { target: { value: 'Bunk daily' } });
    fireEvent.click(screen.getByTestId('lt-builder-save'));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const body = postMock.mock.calls[0][1];
    expect(body.subject_mode).toBe('single_subject');
    expect(body.assignment_scope).toBe('per_subject_in_group');
    expect(body.assignment_group_types).toContain('bunk');
  });

  it('flags missing prompts as a validation issue before save', async () => {
    renderNew();
    fireEvent.click(screen.getByTestId('lt-builder-add-text'));
    fireEvent.click(screen.getByTestId('lt-builder-save'));
    await waitFor(() => expect(screen.getByTestId('lt-builder-issues')).toBeInTheDocument());
    expect(postMock).not.toHaveBeenCalled();
  });

  it('lists Tier 1 field types in the add menu and not Tier 2', () => {
    renderNew();
    expect(screen.getByTestId('lt-builder-add-text')).toBeInTheDocument();
    expect(screen.getByTestId('lt-builder-add-textarea')).toBeInTheDocument();
    expect(screen.getByTestId('lt-builder-add-text_list')).toBeInTheDocument();
    expect(screen.getByTestId('lt-builder-add-single_choice')).toBeInTheDocument();
    expect(screen.getByTestId('lt-builder-add-multiple_choice')).toBeInTheDocument();
    expect(screen.getByTestId('lt-builder-add-rating_group')).toBeInTheDocument();
    expect(screen.queryByTestId('lt-builder-add-yes_no')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lt-builder-add-date')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lt-builder-add-number')).not.toBeInTheDocument();
  });

  it('"Assign form" button is disabled (greyed out) when template status is draft', async () => {
    const draftTemplate = {
      id: 20,
      name: 'Draft Template',
      slug: 'draft-template',
      role: 'counselor',
      languages: ['en'],
      cadence: 'daily',
      subject_mode: 'self',
      assignment_scope: 'none',
      assignment_group_types: [],
      status: 'draft',
      is_active: false,
      version: 1,
      schema: { fields: [] },
    };
    renderEdit(draftTemplate);
    // Wait for template to load
    await waitFor(() =>
      expect(screen.getByTestId('lt-builder-assign-disabled')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('lt-builder-assign-disabled')).toBeDisabled();
    expect(screen.queryByTestId('lt-builder-assign')).not.toBeInTheDocument();
  });

  it('"Assign form" button is enabled on a published template and opens the dialog', async () => {
    const publishedTemplate = {
      id: 10,
      name: 'Published Template',
      slug: 'published-template',
      role: 'counselor',
      languages: ['en'],
      cadence: 'daily',
      subject_mode: 'self',
      assignment_scope: 'none',
      assignment_group_types: [],
      status: 'published',
      is_active: true,
      version: 1,
      schema: { fields: [] },
    };
    renderEdit(publishedTemplate);

    // Wait for the template to load
    await waitFor(() =>
      expect(screen.getByTestId('lt-builder-assign')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('lt-builder-assign')).not.toBeDisabled();
    expect(screen.queryByTestId('lt-builder-assign-disabled')).not.toBeInTheDocument();

    // Clicking opens the dialog
    fireEvent.click(screen.getByTestId('lt-builder-assign'));
    await waitFor(() =>
      expect(screen.getByTestId('assign-form-dialog')).toBeInTheDocument(),
    );
  });

  it('shows the "Form assignments" section on a published template', async () => {
    const publishedTemplate = {
      id: 11,
      name: 'Another Published',
      slug: 'another-published',
      role: 'counselor',
      languages: ['en'],
      cadence: 'daily',
      subject_mode: 'self',
      assignment_scope: 'none',
      assignment_group_types: [],
      status: 'published',
      is_active: true,
      version: 1,
      schema: { fields: [] },
    };
    renderEdit(publishedTemplate);

    await waitFor(() =>
      expect(screen.getByTestId('assignment-list-section')).toBeInTheDocument(),
    );
  });
});
