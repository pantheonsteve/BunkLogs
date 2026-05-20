# Story 1: Sign in with Google on a phone

**As a Counselor, I want to sign in with Google on my phone so I can get into the app quickly without remembering a password.**

## Acceptance criteria

1. The unauthenticated landing screen presents "Continue with Google" as the only primary action.
2. Tapping "Continue with Google" hands off to the device's native Google account picker (system browser or in-app SSO surface, not a webview that re-prompts for password).
3. A successful auth lands the user directly on their role dashboard with no intermediate welcome screen.
4. If the authenticated Google account has no active Counselor Membership in any program, the user sees: *"This account isn't set up as a counselor at [org]. Contact your admin."* with a "Sign out" action.
5. If the authenticated Google account has multiple active Counselor Memberships across orgs, the user picks the active org before reaching the dashboard. Their selection is remembered for the session.
6. If the account is suspended or the Membership is inactive, the error message names the condition and provides a "Sign out" action.

## Design notes

- Email/password is supported by `django-allauth` underneath but should not be promoted in the UI for camp staff.
- "Active org" selection in criterion 5 is rare in practice but real (a multi-summer veteran working at two URJ camps).
