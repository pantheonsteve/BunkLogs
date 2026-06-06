/**
 * Constants and helpers for ReflectionTemplate "routing" fields:
 * cadence, subject_mode, assignment_scope, assignment_group_types,
 * author_role_filter, subject_role_filter, subject_visible.
 *
 * Mirrored from `backend/bunk_logs/core/models.py`:
 *   - Membership.ROLES                  -> ROLE_OPTIONS
 *   - AssignmentGroup.GROUP_TYPES       -> GROUP_TYPE_OPTIONS
 *   - ReflectionTemplate.CADENCES       -> CADENCE_OPTIONS
 *   - ReflectionTemplate.SUBJECT_MODES  -> SUBJECT_MODE_OPTIONS
 *   - ReflectionTemplate.ASSIGNMENT_SCOPES (auto-derived from subject_mode
 *     by `assignmentScopeFor`, since `validate_template_coherence` enforces
 *     a one-to-one mapping anyway).
 */

export const CADENCE_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Biweekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'on_demand', label: 'On Demand' },
];

export const SUBJECT_MODE_OPTIONS = [
  {
    value: 'self',
    label: 'Self-reflection',
    description: 'The author reflects about themselves. One submission per author per period.',
    appearsOn: 'My Tasks, Reflections dashboard',
  },
  {
    value: 'single_subject',
    label: 'About one person at a time',
    description: 'Author files one submission per subject (e.g. one form per camper, per day). Recommended for bunk logs.',
    appearsOn: 'My Tasks, Bunk Logs dashboard, group dashboard',
  },
  {
    value: 'multi_subject',
    label: 'About several people in one submission',
    description: 'One form names multiple people with shared answers (rare). Today My Tasks still works one person at a time—use single-subject for standard bunk logs.',
    appearsOn: 'My Tasks, Bunk Logs dashboard, group dashboard',
  },
  {
    value: 'group',
    label: 'About a group as a whole',
    description: 'One submission per group (e.g. one daily bunk note, no per-camper detail).',
    appearsOn: 'My Tasks, Bunk Logs dashboard, group dashboard',
  },
];

export const GROUP_TYPE_OPTIONS = [
  { value: 'bunk', label: 'Bunk' },
  { value: 'classroom', label: 'Classroom' },
  { value: 'caseload', label: 'Caseload' },
  { value: 'unit', label: 'Unit' },
  { value: 'division', label: 'Division' },
  { value: 'cohort', label: 'Cohort' },
  { value: 'team', label: 'Team' },
  { value: 'specialty', label: 'Specialty / Activity' },
  { value: 'custom', label: 'Custom' },
];

export const ROLE_OPTIONS = [
  { value: 'camper', label: 'Camper' },
  { value: 'counselor', label: 'Counselor' },
  { value: 'junior_counselor', label: 'Junior Counselor' },
  { value: 'specialist', label: 'Specialist' },
  { value: 'general_counselor', label: 'General Counselor' },
  { value: 'unit_head', label: 'Unit Head' },
  { value: 'leadership_team', label: 'Leadership Team' },
  { value: 'kitchen_staff', label: 'Kitchen Staff' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'administrative_staff', label: 'Administrative Staff' },
  { value: 'housekeeping', label: 'Housekeeping' },
  { value: 'camper_care', label: 'Camper Care' },
  { value: 'health_center', label: 'Health Center' },
  { value: 'medical', label: 'Medical' },
  { value: 'special_diets', label: 'Special Diets' },
  { value: 'madrich', label: 'Madrich' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'admin', label: 'Admin' },
];

/**
 * Derive `assignment_scope` from `subject_mode`. The backend's
 * `validate_template_coherence` enforces this exact mapping, so exposing the
 * scope as a separate control would just let the user trip a 400. We compute
 * it on save instead and keep the UI focused on the user-facing decision.
 */
export function assignmentScopeFor(subjectMode) {
  switch (subjectMode) {
    case 'self':
      return 'none';
    case 'group':
      return 'per_group';
    case 'single_subject':
    case 'multi_subject':
      return 'per_subject_in_group';
    default:
      return 'none';
  }
}

export function subjectModeNeedsGroups(subjectMode) {
  return subjectMode !== 'self';
}
