import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SubjectDetail from '../SubjectDetail';

vi.mock('../../../api/observations', () => ({
  fetchRecipientCandidates: vi.fn(() => Promise.resolve([])),
  searchObservationSubjects: vi.fn(() => Promise.resolve([])),
  createObservation: vi.fn(),
  sensitivityAudience: (value) => value,
  SENSITIVITY_OPTIONS: [
    { value: 'normal', label: 'Normal' },
  ],
}));

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
          key: 'request_unit_head_help',
          type: 'single_choice',
          prompts: { en: 'Unit Head help requested' },
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
          request_unit_head_help: { yes: 0, no: 3, total: 3 },
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

function renderDetail(extra = {}, props = {}) {
  const full = { ...payload, ...extra };
  return render(
    <MemoryRouter>
      <SubjectDetail payload={full} personId={221} {...props} />
    </MemoryRouter>,
  );
}

describe('SubjectDetail', () => {
  it('shows a back link to the group dashboard when group query param is set', () => {
    renderDetail({}, { backGroupId: '36', backDate: '2026-05-23' });
    const back = screen.getByTestId('profile-back-to-group');
    expect(back).toHaveAttribute('href', '/dashboards/group/36?date=2026-05-23');
    expect(back).toHaveTextContent('← Back to RBAC Bulk Bunk 5');
  });

  it('shows a back link when the subject belongs to a single bunk', () => {
    renderDetail();
    const back = screen.getByTestId('profile-back-to-group');
    expect(back).toHaveAttribute('href', '/dashboards/group/36');
    expect(back).toHaveTextContent('← Back to RBAC Bulk Bunk 5');
  });

  it('hides the back link when the subject has multiple bunks and no group param', () => {
    renderDetail({
      subject_profile: {
        ...payload.subject_profile,
        assignment_groups: [
          { id: 36, name: 'Bunk A', group_type: 'bunk' },
          { id: 37, name: 'Bunk B', group_type: 'bunk' },
        ],
      },
    });
    expect(screen.queryByTestId('profile-back-to-group')).not.toBeInTheDocument();
  });

  it('renders the profile header with role, program, and bunk chips', () => {
    renderDetail();
    const header = screen.getByTestId('subject-profile-header');
    expect(within(header).getByText('BulkCamper5 #1')).toBeInTheDocument();
    // Preferred-name parenthetical sits inside the H1.
    expect(within(header).getByText(/\(BulkCamper5\)/)).toBeInTheDocument();
    expect(within(header).getByText('camper')).toBeInTheDocument();
    expect(within(header).getByText(/URJ Crane Lake/)).toBeInTheDocument();
    // Group chips link to the consolidated group dashboard.
    const bunkLink = within(header).getByRole('link', { name: /RBAC Bulk Bunk 5/ });
    expect(bunkLink).toHaveAttribute('href', '/dashboards/group/36');
  });

  it('renders KPI tiles for total reflections and yes/no flag counts', () => {
    renderDetail();
    const kpis = screen.getByTestId('subject-kpis-16');
    expect(within(kpis).getByText('Total reflections')).toBeInTheDocument();
    expect(within(kpis).getByText('3')).toBeInTheDocument();
    // request_camper_care_help: 1 yes / 3 total
    expect(within(kpis).getByText('1 / 3')).toBeInTheDocument();
    // not_on_camp + unit head help: 0 yes / 3 total each
    expect(within(kpis).getAllByText('0 / 3').length).toBeGreaterThanOrEqual(2);
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

    // Group dashboard link for the reflection's assignment group on that date.
    expect(within(row228).getByRole('link', { name: /RBAC Bulk Bunk 5/ })).toHaveAttribute(
      'href', '/dashboards/group/36?date=2026-05-23',
    );
  });

  it('shows help request badges when help was requested in the period', () => {
    renderDetail();
    expect(screen.getByTestId('subject-help-badges')).toBeInTheDocument();
    expect(screen.getByTestId('subject-help-request_camper_care_help')).toBeInTheDocument();
    expect(screen.queryByTestId('subject-help-request_unit_head_help')).not.toBeInTheDocument();
  });

  it('shows unit head help badge for boolean true answers', () => {
    renderDetail({
      templates: [{
        ...payload.templates[0],
        reflections: [{
          ...payload.templates[0].reflections[0],
          answers: {
            ...payload.templates[0].reflections[0].answers,
            request_unit_head_help: true,
            request_camper_care_help: 'no',
          },
        }],
      }],
    });
    expect(screen.getByTestId('subject-help-request_unit_head_help')).toBeInTheDocument();
    expect(within(screen.getByTestId('subject-row-228')).getByTestId(
      'subject-flag-16-request_unit_head_help',
    )).toBeInTheDocument();
  });

  it('renders the empty state when there are no templates', () => {
    renderDetail({ templates: [] });
    expect(screen.getByTestId('subject-empty')).toBeInTheDocument();
  });

  it('shows Note + on form-response rows when personId is set', () => {
    renderDetail();
    expect(screen.getByTestId('subject-add-observation-228')).toHaveTextContent('Note +');
  });

  it('opens observation composer prepopulated from a form-response row', async () => {
    renderDetail();
    fireEvent.click(screen.getByTestId('subject-add-observation-228'));
    await waitFor(() => {
      expect(screen.getByTestId('observation-composer-observed-at')).toHaveValue('2026-05-23T12:00');
    });
    expect(screen.getByTestId('observation-subject-chips')).toHaveTextContent('BulkCamper5 #1');
  });

  it('calls onRangeChange when custom start/end dates are selected', () => {
    const onRangeChange = vi.fn();
    renderDetail({}, { onRangeChange });

    fireEvent.change(screen.getByTestId('subject-period-start'), {
      target: { value: '2026-05-01' },
    });
    expect(onRangeChange).toHaveBeenCalledWith('2026-05-01', '2026-05-23');

    onRangeChange.mockClear();
    fireEvent.change(screen.getByTestId('subject-period-end'), {
      target: { value: '2026-05-31' },
    });
    expect(onRangeChange).toHaveBeenCalledWith('2026-05-21', '2026-05-31');
  });

  it('shows observations empty state when none in the selected period', () => {
    renderDetail({ observations: [] });
    expect(screen.getByTestId('observations-empty')).toHaveTextContent(
      'No observations in this period.',
    );
  });

  it('renders observations returned for the selected period', () => {
    renderDetail({
      observations: [
        {
          id: 42,
          body: '<p>Swim note</p>',
          sensitivity: 'normal',
          context: 'swim_instruction',
          observed_at: '2026-05-23T15:00:00Z',
          author: { id: 9, name: 'BulkCounselor #9' },
        },
      ],
    });
    const panel = screen.getByTestId('observations-panel');
    expect(within(panel).getByText('Swim note')).toBeInTheDocument();
    expect(within(panel).getByText('BulkCounselor #9')).toBeInTheDocument();
    const when = within(panel).getByTestId('observation-when-42');
    expect(when).toHaveAttribute('dateTime', '2026-05-23T15:00:00Z');
    expect(when.textContent).toBeTruthy();
  });

  it('pre-fills observation date from panel when viewing a single day', async () => {
    renderDetail({}, { rangeStart: '2026-05-23', rangeEnd: '2026-05-23' });
    fireEvent.click(screen.getByTestId('observation-add-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('observation-composer-observed-at')).toHaveValue(
        '2026-05-23T12:00',
      );
    });
  });

});
