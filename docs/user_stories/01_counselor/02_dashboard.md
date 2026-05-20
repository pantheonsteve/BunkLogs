# Story 2: Land on a dashboard that shows what I owe today

**As a Counselor, when I open the app I want my dashboard to show me everything I'm responsible for today and how much of it is done.**

## Acceptance criteria

1. The post-login screen is the Counselor dashboard. No interstitials, no role selection, no announcements.
2. The dashboard displays three sections, in this order, each with a clear completion state (none / in-progress / complete):
   1. **Camper reflections** — count of reflections submitted vs. expected for the user's bunk roster today
   2. **My self-reflection** — submission state for today
   3. **My requests** — count of any open camper-care or maintenance requests the user submitted (this section has no "incomplete" state; see Story 9)
3. The current date is visible in the dashboard header, formatted in the user's locale.
4. The date the dashboard considers "today" is determined by a single org-level **rollover hour** setting (Story 58). Camp orgs default to 04:00 in the org's timezone; religious-school orgs default to 00:00.
5. Each section's completion state is derived server-side from the underlying data, not stored on the section itself. Refreshing the dashboard reflects state changes made by co-counselors since the last load.
6. The dashboard's first contentful paint completes in under 2 seconds on a representative mid-tier Android phone over 4G.

## Design notes

- Sections need distinct visual treatment for the three states. "Done" should look different enough from "in progress" that a counselor scanning at arm's length can tell the difference.
- The dashboard is the user's primary workspace — not a navigation hub.
