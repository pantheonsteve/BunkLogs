/**
 * The Admin sidebar, as data.
 *
 * Seven destinations, flat. The previous shape had text sub-headings
 * ("Forms", "Reports", "Setup") over thirteen links; those headings are
 * now real pages, so the sidebar stays short and the long lists live on
 * the hub pages that `adminFormLinks` and `adminReportLinks` feed.
 *
 * `icon` is a key the Sidebar maps to a component, and `badge` a key into
 * the counts object the layout fetches, keeping this module plain data so
 * nav shape is testable without rendering anything.
 *
 * The Groups link stays "Groups" for every organization. Group types
 * (Bunk, Classroom, Unit, and the rest) live under that page, so the
 * nav does not rename it to a tenant's word for one of those types.
 */

/** Contents of the /admin/forms hub, and the reason the nav item exists. */
export function adminFormLinks() {
  return [
    {
      to: '/admin/templates',
      label: 'Templates',
      description: 'The reflection forms people fill in.',
    },
    {
      to: '/admin/field-keys',
      label: 'Form fields',
      description: 'Shared field names so dashboards can report across forms.',
    },
  ];
}

/**
 * Contents of the /admin/reports hub. Empty for an org with neither
 * surface, which is also what hides the Reports item from the sidebar.
 *
 * Growth and availability follow the reflection_completion setting.
 * Completion itself lives on the Reflections dashboard.
 *
 * @param {{campOps: boolean, gradeReflections: boolean}} surfaces
 * @param {{reflectionCompletion?: boolean}} [options]
 */
export function adminReportLinks(surfaces, { reflectionCompletion = false } = {}) {
  const links = [];
  if (reflectionCompletion) {
    links.push(
      {
        to: '/admin/reflections/growth',
        label: 'Growth by grade',
        description: 'How each grade is trending across the year.',
      },
      {
        to: '/admin/reflections/availability',
        label: 'Availability',
        description: 'Who is free for which sessions.',
      },
    );
  }
  if (surfaces.campOps) {
    links.push({
      to: '/admin/catalog/planning',
      label: 'Request planning',
      description: 'What has been requested and what still needs ordering.',
    });
  }
  return links;
}

/** Setup destinations, some of which only exist for some orgs. */
export function adminSetupLinks(surfaces, term) {
  const links = [];
  if (surfaces.campOps) {
    links.push({
      to: '/admin/catalog',
      label: 'Request catalog',
      description: 'Stores, request types and the items people can ask for.',
    });
  }
  links.push({
    to: '/admin/setup',
    label: term('program', { plural: true, capitalize: true }),
    description: `Create and end the ${term('program', { plural: true })} everything else hangs off.`,
  });
  return links;
}

/**
 * Admin nav: seven items, top to bottom.
 *
 * @param {{campOps: boolean, gradeReflections: boolean}} surfaces
 * @param {Function} [_term]
 * @param {{reflectionCompletion?: boolean}} [options]
 * @returns {Array<{to: string, label: string, icon: string, badge?: string, end?: boolean}>}
 */
export function adminNavItems(surfaces, _term, { reflectionCompletion = false } = {}) {
  const items = [
    { to: '/admin/home', label: 'Home', icon: 'dashboard', end: true, placement: 'home' },
    {
      to: '/admin/people',
      label: 'People',
      icon: 'people',
      placement: 'manage',
    },
    {
      to: '/admin/groups',
      label: 'Groups',
      icon: 'groups',
      badge: 'groupsNeedingAttention',
      placement: 'manage',
    },
    { to: '/admin/forms', label: 'Forms', icon: 'forms', placement: 'manage' },
  ];

  if (adminReportLinks(surfaces, { reflectionCompletion }).length) {
    items.push({ to: '/admin/reports', label: 'Reports', icon: 'reports', placement: 'manage' });
  }

  items.push(
    { to: '/admin/setup', label: 'Setup', icon: 'setup', placement: 'footer' },
    { to: '/admin/settings', label: 'Settings', icon: 'settings', placement: 'footer' },
  );

  return items;
}

/**
 * Leadership Team owns templates, not the org, so they get the one link
 * rather than the Forms hub -- /admin/field-keys is admin-only.
 */
export function leadershipNavItems() {
  return [{ to: '/admin/templates', label: 'Templates', icon: 'forms' }];
}
