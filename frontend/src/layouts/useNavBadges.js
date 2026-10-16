import { useEffect, useState } from 'react';

import { fetchAdminNavBadges } from '../api/admin';
import { useAdminProgram } from '../context/AdminProgramContext';

/**
 * Sidebar counts for the admin and dashboards shells. Refetched when the
 * program changes and left null on failure, which renders no badge.
 */
export default function useNavBadges() {
  const { programId, ready } = useAdminProgram();
  const [badges, setBadges] = useState(null);

  useEffect(() => {
    if (!ready) return undefined;
    let cancelled = false;
    fetchAdminNavBadges(programId ? { program: programId } : {})
      .then((data) => {
        if (cancelled) return;
        setBadges(data && {
          peopleNeverInvited: data.people_never_invited,
          groupsNeedingAttention: data.groups_needing_attention,
          setupProgress: data.setup_progress,
          questionsForYou: data.questions_for_you,
        });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [programId, ready]);

  return badges;
}
