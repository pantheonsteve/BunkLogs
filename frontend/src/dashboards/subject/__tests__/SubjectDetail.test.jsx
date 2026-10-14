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

  it('renders one daily-log row per reflection, newest first, with rating cells, note, and flag badge', () => {
    renderDetail();
    const rows = within(screen.getByTestId('subject-table-16')).getAllByTestId(/^subject-row-/);
    expect(rows.map((r) => r.dataset.testid)).toEqual(['subject-row-228', 'subject-row-234']);

    const [row228, row234] = rows;
    expect(within(row228).getByLabelText('Behavior 5 of 5')).toBeInTheDocument();
    expect(within(row234).getByLabelText('Behavior 4 of 5')).toBeInTheDocument();
    expect(within(row228).getByText('Solid day overall.')).toBeInTheDocument();
    expect(within(row228).getByText('BulkCounselor #9')).toBeInTheDocument();

    expect(within(row228).getByTestId('subject-log-open-228')).toHaveAttribute(
      'href',
      '/reflections/228',
    );
    expect(within(row228).getByTestId('subject-flag-16-request_camper_care_help')).toBeInTheDocument();
    expect(within(row234).queryByTestId('subject-flag-16-request_camper_care_help')).not.toBeInTheDocument();
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

  it('drives the start/end range from the period toggle', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 4, 23, 12));
    try {
      const onRangeChange = vi.fn();
      renderDetail({}, { onRangeChange });
      fireEvent.click(screen.getByTestId('subject-period-week'));
      expect(onRangeChange).toHaveBeenCalledWith('2026-05-17', '2026-05-23');
      fireEvent.click(screen.getByTestId('subject-period-4weeks'));
      expect(onRangeChange).toHaveBeenCalledWith('2026-04-26', '2026-05-23');
      // No session dates on the profile, so "Full session" isn't offered.
      expect(screen.queryByTestId('subject-period-session')).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
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

  it('shows "This week" KPIs vs the prior period and hides sensitive notes behind the placeholder', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 6, 13, 12));
    try {
      const social = [4, 4, 5, 4, 4, 5, 4, 4, 3, 4, 3, 3, 2];
      const behavior = [4, 4, 4, 5, 4, 4, 4, 3, 3, 3, 2, 3, 2];
      const reflections = social.map((s, i) => ({
        id: 500 + i,
        date: `2026-07-${String(i + 1).padStart(2, '0')}`,
        author_name: 'Maya Levin',
        team_visibility: 'team',
        answers: {
          camper_scores: { social: s, behavior: behavior[i], participation: 4 },
          request_unit_head_help: i === 10 || i === 12 ? 'yes' : 'no',
        },
      }));
      const block = (rows) => ({ ...payload.templates[0], reflections: rows });
      render(
        <MemoryRouter>
          <SubjectDetail
            payload={{
              ...payload,
              period: { start: '2026-07-07', end: '2026-07-13' },
              templates: [block(reflections.slice(6))],
              observations: [{ id: 1, body: '<p>Visible note</p>', sensitivity: 'normal', author: { id: 2, name: 'Jess' }, observed_at: '2026-07-12T15:00:00Z' }],
              hidden_observations: [{ sensitivity: 'domain', count: 1, gating_role: 'Leadership Team and above' }],
            }}
            priorTemplates={[block(reflections.slice(0, 6))]}
            groupPayload={{
              roster: [
                { person_id: 9, name: 'Maya Levin', role_in_group: 'author' },
                { person_id: 221, name: 'BulkCamper5 #1', role_in_group: 'subject' },
                { person_id: 222, name: 'Ilan Gross', role_in_group: 'subject' },
              ],
              help_requested: [{ id: 222 }],
            }}
            rangeStart="2026-07-07"
            rangeEnd="2026-07-13"
            personId={221}
          />
        </MemoryRouter>,
      );

      expect(screen.getByTestId('subject-period-week')).toHaveAttribute('aria-pressed', 'true');

      // Social: this week 23/7 = 3.29; prior 26/6 = 4.33.
      const socialKpi = screen.getByTestId('subject-kpi-camper_scores__social');
      expect(within(socialKpi).getByText('3.3')).toBeInTheDocument();
      expect(within(socialKpi).getByTestId('kpi-delta')).toHaveTextContent('down 1.0');
      expect(within(socialKpi).getByText('vs prior week')).toBeInTheDocument();
      // Behavior: 20/7 = 2.86; prior 25/6 = 4.17.
      const behaviorKpi = screen.getByTestId('subject-kpi-camper_scores__behavior');
      expect(within(behaviorKpi).getByText('2.9')).toBeInTheDocument();
      expect(within(behaviorKpi).getByTestId('kpi-delta')).toHaveTextContent('down 1.3');
      expect(within(socialKpi).getAllByRole('img')).toHaveLength(7);

      expect(screen.getByTestId('subject-help-request_unit_head_help')).toHaveTextContent('2 of last 7 days');
      expect(screen.getAllByTestId('trend-help-band')).toHaveLength(2);

      const panel = screen.getByTestId('observations-panel');
      expect(within(panel).getByText('Visible note')).toBeInTheDocument();
      expect(within(panel).getByTestId('sensitive-note-placeholder')).toHaveTextContent(
        '1 sensitive note (Leadership Team and above)',
      );

      expect(screen.getByTestId('subject-staff-line')).toHaveTextContent('Counselor: Maya Levin');
      const rail = screen.getByTestId('profile-rail-roster');
      expect(within(rail).getByRole('link', { name: 'BulkCamper5 #1' })).toHaveAttribute('aria-current', 'page');
      expect(within(rail).getByTestId('rail-help-dot-222')).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
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
