/**
 * The sentence from the audience preview, shown before an assignment is saved.
 */
import { useEffect, useState } from 'react';

import { previewAssignmentAudience } from '../../api/leadershipTeam';

export function useAudiencePreview({ orgSlug, templateId, targetType, role, groupIds }) {
  const [preview, setPreview] = useState(null);
  const ids = (groupIds || []).map(String).sort().join(',');

  useEffect(() => {
    const wantsRole = targetType === 'role' && role;
    const wantsGroups = targetType === 'assignment_group' && ids;
    if (!templateId || (!wantsRole && !wantsGroups)) {
      setPreview(null);
      return undefined;
    }
    let cancelled = false;
    previewAssignmentAudience(orgSlug, templateId, {
      targetType,
      role: wantsRole ? role : undefined,
      groupIds: wantsGroups ? ids.split(',') : [],
    })
      .then((data) => {
        if (!cancelled && data && typeof data.sentence === 'string') setPreview(data);
        else if (!cancelled) setPreview(null);
      })
      .catch(() => { if (!cancelled) setPreview(null); });
    return () => { cancelled = true; };
  }, [orgSlug, templateId, targetType, role, ids]);

  return preview;
}

export default function AudiencePreview({ preview }) {
  if (!preview?.sentence) return null;
  const blocked = preview.can_assign === false;
  return (
    <p
      className={`text-sm rounded-md px-3 py-2 ${
        blocked
          ? 'bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
          : 'bg-gray-50 text-gray-700 dark:bg-gray-900/40 dark:text-gray-200'
      }`}
      data-testid="audience-preview"
    >
      {preview.sentence}
    </p>
  );
}
