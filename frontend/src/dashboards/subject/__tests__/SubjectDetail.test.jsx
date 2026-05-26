import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SubjectDetail from '../SubjectDetail';

const payload = {
  subject: {
    id: 221,
    name: 'BulkCamper5 #1',
    preferred_name: 'BulkCamper5',
  },
  subject_profile: {
    id: 221,
    full_name: 'BulkCamper5 #1',
    preferred_name: 'BulkCamper5',
    preferred_language: 'en',
    primary_role: 'camper',
    programs: [{ id: 1, name: 'URJ Crane Lake Camp - Summer 2026', role: 'camper' }],
    assignment_groups: [{ id: 36, name: 'RBAC Bulk Bunk 5', group_type: 'bunk' }],
  },
  period: { start: '2026-05-21', end: '2026-05-23' },
  templates: [
    {
      template: {
        id: 16,
        name: 'RBAC test — Camper daily check-in',
        slug: 'rbac-test-bunk-daily',
        subject_mode: 'single_subject',
      },
      schema_fields: [
        {
          key: 'not_on_camp',
          type: 'single_choice',
          prompts: { en: 'Camper not on camp today' },
          options: [
            { value: 'no', labels: { en: 'No' } },
            { value: 'yes', labels: { en: 'Yes' } },
          ],
        },
        {
          key: 'request_camper_care_help',
          type: 'single_choice',
          prompts: { en: 'Camper Care help requested' },
          options: [
            { value: 'no', labels: { en: 'No' } },
            { value: 'yes', labels: { en: 'Yes' } },
          ],
        },
        {
          key: 'camper_scores',
          type: 'rating_group',
          scale: [1, 5],
          categories: [
            { key: 'behavior', labels: { en: 'Behavior' } },
            { key: 'participation', labels: { en: 'Participation' } },
            { key: 'social', labels: { en: 'Social' } },
          ],
        },
        {
          key: 'daily_report',
          type: 'textarea',
          prompts: { en: 'Daily report' },
        },
      ],
      summary: {
        total_reflections: 3,
        flag_counts: {
          not_on_camp: { yes: 0, no: 3, total: 3 },
          request_camper_care_help: { yes: 1, no: 2, total: 3 },
        },
      },
      rating_series: [
        {
          label: 'camper_scores__behavior',
          scale_max: 5,
          points: [
            { date: '2026-05-21', value: 3, reflection_id: 240, scale_max: 5, team_visibility: 'team' },
            { date: '2026-05-22', value: 4, reflection_id: 234, scale_max: 5, team_visibility: 'team' },
            { date: '2026-05-23', value: 5, reflection_id: 228, scale_max: 5, team_visibility: 'team' },
          ],
        },
      ],
      reflections: [
        {
          id: 228,
          date: '2026-05-23',
          author_name: 'BulkCounselor #9',
          team_visibility: 'team',
          language: 'en',
          answers: {
            not_on_camp: 'no',
            request_camper_care_help: 'yes',
            camper_scores: { behavior: 5, participation: 4, social: 5 },
            daily_report: 'Solid day overall.',
          },
          assignment_group: { id: 36, name: 'RBAC Bulk Bunk 5' },
        },
        {
          id: 234,
          date: '2026-05-22',
          author_name: 'BulkCounselor #9',
          team_visibility: 'team',
          language: 'en',
          answers: {
            not_on_camp: 'no',
            request_camper_care_help: 'no',
            camper_scores: { behavior: 4, participation: 5, social: 4 },
            daily_report: 'Engaged in archery.',
          },
          assignment_group: { id: 36, name: 'RBAC Bulk Bunk 5' },
        },
      ],
    },
  ],
  recent_texts: [
    {
      reflection_id: 228,
      template_id: 16,
      template_name: 'RBAC test — Camper daily check-in',
      field_key: 'daily_report',
      text: 'Solid day overall.',
      date: '2026-05-23',
      author_name: 'BulkCounselor #9',
      team_visibility: 'team',
    },
  ],
  concerning_patterns: [],
};

function renderDetail(extra = {}) {
  const full = { ...payload, ...extra };
  return render(
    <MemoryRouter>
      <SubjectDetail payload={full} />
    </MemoryRouter>,
  );
}

describe('SubjectDetail', () => {
  it('renders the profile header with role, program, and bunk chips', () => {
    renderDetail();
    const header = screen.getByTestId('subject-profile-header');
    expect(within(header).getByText('BulkCamper5 #1')).toBeInTheDocument();
    // Preferred-name parenthetical sits inside the H1.
    expect(within(header).getByText(/\(BulkCamper5\)/)).toBeInTheDocument();
    expect(within(header).getByText('camper')).toBeInTheDocument();
    expect(within(header).getByText(/URJ Crane Lake/)).toBeInTheDocument();
    // The bunk chip is wrapped in a link to the subject-trends grid.
    const bunkLink = within(header).getByRole('link', { name: /RBAC Bulk Bunk 5/ });
    expect(bunkLink).toHaveAttribute('href', '/dashboards/subject-trends/36');
  });

  it('renders KPI tiles for total reflections and yes/no flag counts', () => {
    renderDetail();
    const kpis = screen.getByTestId('subject-kpis-16');
    expect(within(kpis).getByText('Total reflections')).toBeInTheDocument();
    expect(within(kpis).getByText('3')).toBeInTheDocument();
    // request_camper_care_help: 1 yes / 3 total
    expect(within(kpis).getByText('1 / 3')).toBeInTheDocument();
    // not_on_camp: 0 yes / 3 total
    expect(within(kpis).getByText('0 / 3')).toBeInTheDocument();
  });

  it('renders one form-response row per reflection with colour-coded ratings + flag chip', () => {
    renderDetail();
    const row228 = screen.getByTestId('subject-row-228');
    const row234 = screen.getByTestId('subject-row-234');

    // Rating cells expose value via aria-label "<label>: <n> of <scaleMax>".
    expect(within(row228).getByLabelText('Behavior: 5 of 5')).toBeInTheDocument();
    expect(within(row234).getByLabelText('Behavior: 4 of 5')).toBeInTheDocument();

    // Yes-flag chip rendered only on row 228 (camper_care_help=yes).
    expect(within(row228).getByTestId('subject-flag-16-request_camper_care_help')).toBeInTheDocument();
    expect(within(row234).queryByTestId('subject-flag-16-request_camper_care_help')).not.toBeInTheDocument();

    // Reflection link present.
    expect(within(row228).getByRole('link', { name: /Open/ })).toHaveAttribute(
      'href', '/reflections/228',
    );
  });

  it('renders the empty state when there are no templates', () => {
    renderDetail({ templates: [] });
    expect(screen.getByTestId('subject-empty')).toBeInTheDocument();
  });
});
