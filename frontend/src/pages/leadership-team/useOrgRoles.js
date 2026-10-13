/**
 * Roles and group-type words for the form builder and assignment dialogs.
 *
 * The list is this organization's enabled roles. Labels come from
 * terminology, so a slug never shows up as the words on screen.
 */
import { useEffect, useState } from 'react';

import { getAdminSettings } from '../../api/admin';
import { useTerm } from '../../context/OrgBrandingContext';
import { labeledRoles } from '../../utils/roleLabels';

const FALLBACK_ROLES = [
  'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'administrative_staff', 'housekeeping', 'camper_care', 'health_center', 'medical',
  'madrich', 'faculty',
];

export function groupTypeLabel(type, term, fallback) {
  const fromTerm = term(type, { capitalize: true });
  if (fromTerm && fromTerm.toLowerCase() !== type) return fromTerm;
  return fallback || fromTerm;
}

export function useOrgRoles(currentRole) {
  const term = useTerm();
  const [enabled, setEnabled] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [groupConfig, setGroupConfig] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getAdminSettings()
      .then((data) => {
        if (cancelled || !data) return;
        setEnabled(Array.isArray(data.enabled_roles) ? data.enabled_roles : []);
        setCatalog(Array.isArray(data.role_catalog) ? data.role_catalog : []);
        setGroupConfig(data.group_type_config && typeof data.group_type_config === 'object'
          ? data.group_type_config
          : {});
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const base = enabled?.length ? enabled : FALLBACK_ROLES;
  const roles = currentRole && !base.includes(currentRole) ? [currentRole, ...base] : base;
  const labels = labeledRoles(roles, term, catalog);
  const labelFor = (role) => {
    const index = roles.indexOf(role);
    return index >= 0 ? labels[index] : term(role, { capitalize: true });
  };

  return { roles, labelFor, groupConfig, term };
}

/** Writer and subject roles configured for the checked group types. */
export function seatsFor(groupTypes, groupConfig) {
  const writers = [];
  const subjects = [];
  const seenWriters = new Set();
  const seenSubjects = new Set();
  if (!groupConfig) return { writers, subjects };
  for (const groupType of groupTypes || []) {
    const cfg = groupConfig[groupType];
    if (!cfg || cfg.enabled === false) continue;
    for (const member of cfg.members || []) {
      if (member.placed_as === 'author' && member.role && !seenWriters.has(member.role)) {
        seenWriters.add(member.role);
        writers.push(member.role);
      }
      if (member.placed_as === 'subject' && member.role && !seenSubjects.has(member.role)) {
        seenSubjects.add(member.role);
        subjects.push(member.role);
      }
    }
  }
  return { writers, subjects };
}
