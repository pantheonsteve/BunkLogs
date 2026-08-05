import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SubjectEntriesTable from '../SubjectEntriesTable';
import {
  flattenSubjectEntries,
  subjectEntriesExportUrl,
  subjectEntriesPageLink,
  downloadSubjectEntriesExport,
} from '../flattenSubjectEntries';

vi.mock('../../../api', () => ({
  default: {
    get: vi.fn(),
  },
}));

const payload = {
  templates: [
    {
      template: { id: 1, name: 'Bunk Pulse', slug: 'bunk-pulse' },
      schema_fields: [
        {
          key: 'overall',
          type: 'single_rating',
          prompts: { en: 'Overall' },
          scale: [1, 5],
        },
        {
          key: 'notes',
          type: 'textarea',
          prompts: { en: 'Notes' },
        },
      ],
      reflections: [
        {
          id: 10,
          date: '2026-06-02',
          author_name: 'Counselor One',
          language: 'en',
          team_visibility: 'team',
          answers: { overall: 4, notes: 'Great day' },
        },
      ],
    },
  ],
  observations: [
    {
      id: 20,
      body: '<p>Follow-up note</p>',
      context: 'Check-in',
      observed_at: '2026-06-01T14:00:00-04:00',
      author: { id: 2, name: 'Counselor One' },
    },
  ],
};

describe('flattenSubjectEntries', () => {
  it('merges reflections and observations newest first', () => {
    const entries = flattenSubjectEntries(payload);
    expect(entries).toHaveLength(2);
    expect(entries[0].kind).toBe('reflection');
    expect(entries[0].id).toBe(10);
    expect(entries[1].kind).toBe('observation');
    expect(entries[1].id).toBe(20);
  });

  it('returns empty array for missing payload', () => {
    expect(flattenSubjectEntries(null)).toEqual([]);
  });
});

describe('subjectEntriesExportUrl', () => {
  it('includes date range query params', () => {
    expect(
      subjectEntriesExportUrl(20, { start: '2026-06-01', end: '2026-06-30' }),
    ).toBe('/api/v1/dashboards/subject/20/export/?date_start=2026-06-01&date_end=2026-06-30');
  });
});

describe('downloadSubjectEntriesExport', () => {
  it('requests export with auth-capable api client', async () => {
    const api = (await import('../../../api')).default;
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    vi.stubGlobal('URL', {
      ...globalThis.URL,
      createObjectURL: vi.fn(() => 'blob:test'),
      revokeObjectURL: vi.fn(),
    });
    api.get.mockResolvedValueOnce({
      data: new Blob(['csv']),
      headers: { 'content-disposition': 'attachment; filename="camper_entries.csv"' },
    });
    await downloadSubjectEntriesExport(20, {
      start: '2026-06-01',
      end: '2026-06-30',
      subjectName: 'Lucas Behar',
    });
    expect(api.get).toHaveBeenCalledWith(
      '/api/v1/dashboards/subject/20/export/',
      expect.objectContaining({
        params: { date_start: '2026-06-01', date_end: '2026-06-30' },
        responseType: 'blob',
      }),
    );
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });
});

describe('subjectEntriesPageLink', () => {
  it('builds entries page link with date range', () => {
    expect(
      subjectEntriesPageLink(20, { start: '2026-06-01', end: '2026-06-30' }),
    ).toBe('/profile/20/entries?date_start=2026-06-01&date_end=2026-06-30');
  });
});

describe('SubjectEntriesTable', () => {
  it('renders mixed reflection and observation rows', () => {
    const entries = flattenSubjectEntries(payload);
    render(
      <MemoryRouter>
        <SubjectEntriesTable entries={entries} language="en" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('subject-entries-table')).toBeInTheDocument();
    expect(screen.getByTestId('subject-entry-row-10')).toBeInTheDocument();
    expect(screen.getByTestId('subject-entry-row-20')).toBeInTheDocument();
    expect(screen.getAllByText('Bunk Pulse').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Check-in').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Great day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Follow-up note').length).toBeGreaterThan(0);
  });

  it('shows empty state when no entries', () => {
    render(
      <MemoryRouter>
        <SubjectEntriesTable entries={[]} language="en" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('subject-entries-empty')).toBeInTheDocument();
  });
});
