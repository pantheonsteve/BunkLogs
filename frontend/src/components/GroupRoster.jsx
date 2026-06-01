/**
 * Full member roster for a group dashboard.
 *
 * Renders the `roster` array from `GET /api/v1/dashboards/group/<id>/`
 * (authors first, then subjects). Each member shows their program role
 * (membership_role) and how they participate in the group (role_in_group).
 */

const ROLE_IN_GROUP_LABELS = {
  author: 'Author',
  subject: 'Member',
};

function prettyRole(role) {
  if (!role) return '\u2014';
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function GroupRoster({ roster }) {
  const members = Array.isArray(roster) ? roster : [];

  return (
    <section
      data-testid="group-roster"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-4 mb-6"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-3">
        Roster ({members.length})
      </h2>

      {members.length === 0 ? (
        <p className="text-sm italic text-gray-500 dark:text-gray-400">
          No members assigned to this group.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
                <th className="py-1.5 pr-4 font-medium">Name</th>
                <th className="py-1.5 pr-4 font-medium">Role</th>
                <th className="py-1.5 font-medium">In group as</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {members.map((m) => (
                <tr key={`${m.person_id}-${m.role_in_group}`}>
                  <td className="py-1.5 pr-4 text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {m.name}
                  </td>
                  <td className="py-1.5 pr-4 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {prettyRole(m.membership_role)}
                  </td>
                  <td className="py-1.5 whitespace-nowrap">
                    <span className="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                      {ROLE_IN_GROUP_LABELS[m.role_in_group] || prettyRole(m.role_in_group)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
