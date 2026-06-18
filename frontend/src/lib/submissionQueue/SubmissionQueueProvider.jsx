import { useEffect } from 'react';
import { startQueueDrainLoop, stopQueueDrainLoop } from './queue';

/**
 * Mount once inside authenticated app shell to drain the offline queue
 * on load, periodically, and when connectivity returns.
 */
export default function SubmissionQueueProvider({ children }) {
  useEffect(() => {
    startQueueDrainLoop();
    return () => stopQueueDrainLoop();
  }, []);

  return children;
}
