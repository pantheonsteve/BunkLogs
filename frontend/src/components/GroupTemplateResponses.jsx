/**
 * Assigned-template responses for the unified group dashboard.
 *
 * Renders one `FormResponsesCard` per reflection template assigned to
 * the group (via `TemplateAssignment` with target_type='assignment_group')
 * whose date window contains the selected date. Data shape: see
 * `api/dashboards/group_template_cards.py` (payload key `templates`).
 *
 * Reuses the per-subject dashboard card so the visual treatment matches
 * exactly; `showSubject` adds the Subject column since group rows span
 * multiple people. Each row's **Note +** opens the same observation
 * composer as the per-subject profile page, pre-filled with that camper
 * and the row's camp day.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FormResponsesCard from '../dashboards/subject/responseTable/FormResponsesCard';
import ObservationComposer, { dateOnlyToLocalDatetime } from './observations/ObservationComposer';
import { groupDashboardLink, observationThreadLink, profileLink } from '../utils/dashboardLinks';

export default function GroupTemplateResponses({
  templates = [],
  language = 'en',
  profileLinkContext = null,
  groupLabel = null,
  onNoteCreated = null,
}) {
  const navigate = useNavigate();
  const [composeObservation, setComposeObservation] = useState(null);

  const returnTo = useMemo(() => {
    if (!profileLinkContext?.groupId) return null;
    return groupDashboardLink(profileLinkContext.groupId, {
      date: profileLinkContext.date,
    });
  }, [profileLinkContext]);

  const openCompose = (date, subject) => {
    if (!subject?.id) return;
    setComposeObservation({
      subject: { id: Number(subject.id), full_name: subject.name },
      observedAtLocal: date ? dateOnlyToLocalDatetime(date) : null,
    });
  };

  if (!templates || templates.length === 0) return null;
  return (
    <section className="mt-8" data-testid="group-template-responses">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
        Assigned forms
      </h2>
      {templates.map((block) => (
        <FormResponsesCard
          key={block.template?.id ?? block.assignment?.id}
          block={block}
          language={language}
          testidPrefix="group-template"
          showSubject
          subjectProfileLink={
            profileLinkContext
              ? (id) => profileLink(id, profileLinkContext)
              : null
          }
          onAddObservation={openCompose}
        />
      ))}
      {composeObservation && (
        <ObservationComposer
          initialSubjects={[composeObservation.subject]}
          initialObservedAtLocal={composeObservation.observedAtLocal}
          onClose={() => setComposeObservation(null)}
          onSent={(data) => {
            setComposeObservation(null);
            if (onNoteCreated) onNoteCreated();
            if (data?.id) {
              navigate(observationThreadLink(data.id, returnTo, { contextLabel: groupLabel }));
            }
          }}
        />
      )}
    </section>
  );
}
