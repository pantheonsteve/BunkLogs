# BunkLogs Dashboard Catalog: Camp ↔ School

**As of:** October 12, 2026 (from the code at `fcfe2afc`)
**Purpose:** Every home and dashboard, paired across camp and school, so alignment work is a list rather than a hunt. The code half is done; the **"Trips up a new admin / user"** rows are for Steve to fill in from clicking through both orgs.

**How to read the "why different" labels:**

- **Need:** a real difference in what the customer needs. Keep it, but gate it with a per-org setting or show it when data exists, not by customer type.
- **History:** built at different times for different customers. Converge it.
- **Words:** only the nouns differ. Fix with `useTerm`.

---



## Summary


| #   | Pair                                       | Today                                                                                                              | Verdict                                                                                        |
| --- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| 1   | Admin home (camp) ↔ Director home (school) | One component; school-only tabs switched on customer type                                                          | **Same shell, different sections.** Close. Mostly gating and wording                           |
| 2   | Leadership Team (camp) ↔ Ed Team (school)  | Camp has a separate LT home; TBE has no LT members, so the Ed Team uses the admin home                             | **Structural difference, not a duplicate.** Decide whether schools ever get an LT layer        |
| 3   | Unit Head ↔ Faculty                        | Two components; shared building blocks since 8_5                                                                   | **Same shell, different sections.** Best candidate to merge                                    |
| 4   | Counselor ↔ Madrich                        | Two components; very different layouts                                                                             | **Truly different today**, mostly history. Biggest gap                                         |
| 5   | Camper profile ↔ student/madrich profile   | One shared subject profile (8_6) plus three older camp-only subject views and a separate faculty view of a madrich | **Shared, plus leftovers to retire**                                                           |
| 6   | Camp-only roles                            | Camper Care, Specialist, Kitchen/Housekeeping, Maintenance                                                         | **Keep camp-only for now.** Kitchen home is a generic "staff self-reflection" home in disguise |


**The pattern across all six:** the shared pieces already exist (`GroupCard`, `SupervisorHeading`, `AttentionCard`, `HomeCard`, `DashboardTabs`, `SubjectDetail`). What keeps the pairs apart is (a) the `orgSurfaces()` customer-type switch and (b) madrich/faculty pages that never adopted the camp components, or vice versa.

**One wording and modeling conflict affects pairs 3–5.** TBE's terminology maps `camper` → "student" and `counselor` → "faculty". This matches how the TBE roster import places people: in each classroom, **madrichim are subjects** (faculty observe them) and **faculty are authors**. So the faculty home's "Students" column is actually a list of madrichim, and the madrich home's "Your students" card leads to a classroom whose subjects are madrichim. That model differs from the mapping "Madrich = Counselor, Faculty = Unit Head, Student = Camper": at TBE, faculty are counselor-like (they observe the people in their group) *and* unit-head-like (they answer challenges and review reflections). Settled in favor of Steve's mapping (Madrich = Counselor, Faculty = Unit Head, Student = Camper); prompt `10_2b_tbe_group_placement` moves TBE's placement and terminology onto it.

---



## 1. Admin home ↔ Director home

**Route:** `/admin/home` for both. `AdminHome.jsx` renders five tabs through `DashboardTabs`, which hides any tab with no content. School-only cards come from `DirectorHome.jsx` (`directorSections`), switched on with `orgSurfaces(user).gradeReflections`.


| Tab         | Camp                                                 | School                                                             | Why different                                       | Action                                                                                                    |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Performance | ✅ `PerformanceDashboard`                             | ✅ same                                                             | —                                                   | None                                                                                                      |
| Staffing    | —                                                    | ✅ Sunday coverage (availability)                                   | Need: camps don't use the availability calendar yet | Gate on an "availability" setting, not customer type. Replace "Sunday" with the program's session wording |
| Follow-ups  | —                                                    | ✅ "Questions for you" (routed to Director), Faculty responsiveness | History: camps also route questions (`routes_to`)   | Show whenever routed questions exist. A camp director would use this                                      |
| Insights    | —                                                    | ✅ Themes, Cohort feed moderation                                   | History (themes), Need (cohort feed)                | Themes: show for any org with themes. Cohort feed: gate on whether the feed is enabled                    |
| Program     | ✅ Setup checklist, needs attention, counts, activity | ✅ same                                                             | —                                                   | None. Already uses `term()`                                                                               |


**Hardcoded wording in the school cards:** "Director", "Faculty responsiveness", "Madrichim", "Sunday", "(faculty)". None of it goes through `term()`.

**The admin nav, sidebar and Reports hub are switched the same way** (`adminNavConfig.js`, `Sidebar.jsx`, `ReportsHub.jsx`):


| Item                                                       | Camp                      | School               | Why different                                               | Action                                                                                                             |
| ---------------------------------------------------------- | ------------------------- | -------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Reports: "Madrich completion" (`/admin/reflections`)       | —                         | ✅                    | History: same idea as camp Coverage                         | Merge with Coverage into one "Completion" report with daily or weekly cadence from the template                    |
| Reports: "Growth by grade"                                 | —                         | ✅                    | Need: grade-based                                           | Show when groups have grade levels                                                                                 |
| Reports: "Availability"                                    | —                         | ✅                    | Need                                                        | Same setting as the Staffing tab                                                                                   |
| Reports: Request planning, Setup: Request catalog          | ✅                         | —                    | Need: camp ordering                                         | Gate on a "requests" setting                                                                                       |
| Sidebar: Group Performance, Daily logs, Coverage dashboard | ✅                         | —                    | History                                                     | Group Performance is already on the school admin home tab, so the sidebar hiding it is inconsistent. Show for both |
| Sidebar: Reflections                                       | `/dashboards/reflections` | `/admin/reflections` | History: two different pages under one label                | One Reflections page                                                                                               |
| Sidebar: Observations                                      | ✅                         | —                    | History: madrichim can already add observations on students | Show for both                                                                                                      |
| Sidebar: Maintenance Queue, Camper Care orders             | ✅                         | —                    | Need                                                        | Gate on "requests" / "operations" settings                                                                         |


**Admin-handoff issue found in code:** in Setup → Add/Edit Program (`ProgramAdminModals.jsx`), **Program type is a free-text box** ("e.g. summer_camp"). The value decides which features the whole org sees, and a client admin has no way to know the valid values. Make it a dropdown, or hide it once the per-org settings replace the customer-type switch.

**Trips up a new admin / user:** 

When I add a new staff member, the role dropdown has all of the available roles. There should be only the roles that are relevant to the org. These should be configurable in the admin screen somewhere. For example, I don't need to see the Counselor role as a religious school admin, and I don't need to see the Faculty role as a camp admin.

On [http://localhost:5173/admin/people](http://localhost:5173/admin/people), when I select the person I just added, they do not belong to a group. There should be an option to add them to a group where it says "Not in any groups."

When I go to a group (classroom in the case of the TBE), I have the option to add students or add faculty. These make sense for this type of group, but these roles should be configurable by group type, not hard coded.

As a faculty member of a group, I would think that person would be a supervisor. When I go to their person profile under [http://localhost:5173/admin/people](http://localhost:5173/admin/people), the supervision tab says nothing supervised yet. The configuration of the groups should allow me to define supervisor roles (e.g. Faculty) and supervised roles (e.g. students). I don't see this option.

I want to assign a form to this user, but when I go to their group ([http://localhost:5173/admin/groups/192?tab=members](http://localhost:5173/admin/groups/192?tab=members)), there is no option to assign a form to that group. There should be a button that gives me the available forms to assign to this group, and an indicator of which forms are assigned to this group. I don't see either.

Then, when I go to look for the forms that are assigned to that group ([http://localhost:5173/admin/templates](http://localhost:5173/admin/templates)), I can see if I scroll down that the Class Behavior Report has been assigned to Grade 1 (classroom), but it's really not easy to see. On the groups admin page in the previous paragraph, I should be able to see clearly which forms have been assigned. Also, I can't click on the form and preview it to see what is in it, but I should be able to. And I have no way of assigning the form to the new member of the group if the form has already been assigned to the group and the person has just been added. It is unclear if that person is assigned that form automatically by being added to the group. That indicator should be in that person's admin section ([http://localhost:5173/admin/people](http://localhost:5173/admin/people) when I select a person I should see which forms are assigned to them).

I made a change to the form, then saved it. Does this automatically update if the form is already assigned, or do I need to assign it again? I really don't know.

When I try to create a program, there is no dropdown for the type of program, which is a huge issue. The free form text is a big failure point potential. Only the types of programs that exist should be selectable.

---



## 2. Leadership Team ↔ Ed Team

**Camp:** `/leadership-team` (`pages/leadership-team/Dashboard.jsx`) is a separate non-admin role. It shows My reflection, My teams (supervised roles → team dashboard with submission status, flagged reflections, members), and Bunks & units links. LT members can also reach the template library.
**School:** TBE has no `leadership_team` members. The "Ed Team" is TBE's word for `director`, and those people are admins on the admin home (pair 1).


|     | Camp                                | School              | Why different                                                                                    |
| --- | ----------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------ |
| Who | LT: senior staff who are not admins | Ed Team: the admins | Need: camps have a supervisory layer between the director and unit heads; a small school doesn't |


**Verdict:** this is not duplication. It's one more layer at camps. Two questions decide the work:

1. Would a larger religious school have a non-admin layer (such as a principal's assistant or a grade coordinator)? If so, it uses the LT home with school terminology, and no new page is needed.
2. Should the LT home pick up the school admin cards (Follow-ups, Insights)? A camp LT member would plausibly want "questions routed to me".

**Hardcoded wording:** "Bunks and units", "Leadership Team" in the LT home. There are no `term()` calls in either LT page.

**Trips up a new admin / user:** *(Steve to fill in)*

---



## 3. Unit Head ↔ Faculty

**Camp:** `/unit-head` (`UnitHeadDashboard.jsx`). **School:** `/faculty` (`faculty/Dashboard.jsx`). Since 8_5 both share `GroupCard`, `SupervisorHeading` and `AttentionCard`, and both use `term()`.


| Section               | Unit Head                                      | Faculty                                                    | Why different                                     | Action                                                                                                                                  |
| --------------------- | ---------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Day/week stepper      | ✅ `DayStepper`                                 | —                                                          | Need: daily vs weekly cadence                     | One stepper; its period comes from the template cadence                                                                                 |
| My own reflection     | ✅ badge + Write reflection                     | —                                                          | History: faculty have no self-reflection template | Show when the person has an assigned template                                                                                           |
| Attention cards       | ✅ Unit Head help, Camper Care help, off camp   | Help from you (challenges), Waiting on you (queue), Unread | History: same idea, different sources             | One attention row fed by whatever is routed to this person                                                                              |
| Group grid            | ✅ bunk cards: completion, averages, flags      | ✅ class cards                                              | Words                                             | Already shared                                                                                                                          |
| Selected group roster | Camper scores table (`CamperScoresTable`)      | Madrich roster with availability                           | History + the terminology conflict                | Faculty roster is a list of **staff** in the group, which is the Unit Head's staff section. Students-in-class would be the scores table |
| Staff reflections     | ✅ inline + `/unit-head/staff-reflections` page | Queue (`/faculty/queue`)                                   | History: same job, different shapes               | One "staff reflections" section and page                                                                                                |
| Who's out             | "Not on camp" (campers off camp)               | Upcoming Sundays (staff availability)                      | Need: different people being out                  | Two gated sections: subjects away / staff away                                                                                          |
| Challenges inbox      | —                                              | ✅ `/faculty/challenges`                                    | History                                           | Unit heads would use this. Gate on a "challenges" setting                                                                               |


**Verdict:** the best pair to merge into one supervisor home (step 9.4a in the Wave 9 doc), and it's mostly assembly since the parts are shared.

**Hardcoded wording:** `faculty/Queue.jsx` says "Madrichim".

**Trips up a new admin / user:** 

Logged in as Sadie Allspaw ([http://localhost:5173/faculty](http://localhost:5173/faculty)) 

My Tasks are visible, but they take up the entire above the fold. There should be a tab system to navigate between the different sections of the dashboard. My Tasks should be a tab. Help From You, Class Challenges, and Out should be visible, but they need to be better visually defined so the user knows what each is look for. My Classes look good, should be visible above the fold. There is a full roster of the Madrichim group on the main dashboard, but I can access the group dashboard from the tile, so that should be enough and I do not need to see the full class roster on the Faculty dashboard as long as the tile is there. The upcoming Sundays tile looks good, but it should be more like a calendar than it is.

The navigation on the left is cluttered for this role. My Tasks is there, so maybe that is enough to see the tasks and it does not also need to show the tasks themselves on the faculty dashboard, just a link to the My Tasks page. File a Reflection should be part of My Tasks, and not on the main navigation menu for this role. Challenges looks good, but when I click into an individual challenge, the presentation is not styled and it looks too sparse ([http://localhost:5173/faculty/challenges/a194f6ea-0ad6-4816-873e-67db1c66b25f](http://localhost:5173/faculty/challenges/a194f6ea-0ad6-4816-873e-67db1c66b25f)). I respond to a challenge, which works, but there should be a Done button at the bottom or a return to challenges that is more clearly viewable (although I see it at the top of the page). Hide the Daily Logs navigation link - it shows the daily logs tiles but when I click on those ([http://localhost:5173/dashboards/logs](http://localhost:5173/dashboards/logs)) it simply takes me back to the Home Screen. Reflections should not be there - or roll My Reflections and File a Reflection into the Reflections nav link if they should be there. Keep coverage dashboard - but that link should also be on the Admin navigation, and it's not. Concerns about my unit looks like a good page, but the term "unit" is specific to camp, and not applicable to the temple.

---



## 4. Counselor ↔ Madrich

**Camp:** `/counselor` (`CounselorMobileDashboard.jsx`, 731 lines, phone-first, rebuilt in 8_4). **School:** `/madrich` (`madrich/Dashboard.jsx`, 574 lines, built in 4_9 with `HomeCard`s in Required / Optional bands). They share almost no components.


| Section             | Counselor                                                | Madrich                                                                | Why different                      | Action                                                            |
| ------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------- |
| Layout              | Phone-first, day stepper, bottom tab bar                 | Desktop-width cards, Required/Optional bands                           | History                            | Adopt the 8_4 phone-first layout for madrichim (teens, on phones) |
| Logging on subjects | ✅ per-bunk hero, "Continue logging", camper status chips | "My classrooms" card → group dashboard to add observations on students | History: same job, different depth | One "subjects to log" section, shown when the group has subjects  |
| My own reflection   | ✅ "How was your day?" with streak                        | ✅ "My reflection" (weekly 3-2-1), history link                         | Need: cadence only                 | One section; cadence from template                                |
| Trends              | —                                                        | ✅ `RatingTrendChart` "How I'm doing"                                   | History                            | Counselors would like this too                                    |
| Requests            | ✅ Camper Care + maintenance, "My requests"               | —                                                                      | Need                               | Gate on "requests" setting                                        |
| Challenges          | —                                                        | ✅ "Report a challenge"                                                 | History                            | Gate on "challenges" setting                                      |
| Availability        | —                                                        | ✅ card + nudge                                                         | Need                               | Gate on "availability" setting                                    |
| Cohort feed         | —                                                        | ✅ when cohort enabled                                                  | Need                               | Already data-driven (`cohort.enabled`). Fine                      |
| Quick actions       | ✅ 2×2                                                    | —                                                                      | History                            | Becomes the place the gated actions live                          |


**Hardcoded wording:** the counselor home has **no** `term()` **calls**. "campers logged", "All campers logged", "off camp", "camper(s)", "With {co-counselors}", the "Counselor" heading. It's the most-used page at camps and the least ready for a school. The madrich home hardcodes "Madrich", "Director", "My classrooms", "Your students".

**Verdict:** truly different today, but almost all of it is history. This is the pair to tackle after pair 3. It's also the page TBE's madrichim use weekly, so polishing it helps TBE now.

**Trips up a new admin / user:** 

When I write a concern or something that my supervisor can respond to, it should be very clear. In this case, I logged in as Leo Sobel, and I was able to view the questions I had for the ed team, but it took me too many clicks to see what the response was. This should be visible right from my dashboard and easy to refer back to.

When I visit [http://localhost:5173/madrich/history](http://localhost:5173/madrich/history), I can see only a thumbnail of my response, but I should be able to go back and see the previous response. Also, the Madrich route is only applicable to the religious school, so I need a more universal route that aligns with the counselor's view. The route should use the shared terminology of the two org types.

When logged in as Leo Sobel, on my homepage, I am part of two classrooms (197 and 199), but only the Madrichim classroom comes up as a place to view students, and when I click View Students, it says I don't have access to that group. But if I want to write notes about students, I can't. I don't know where to do that.

I logged a challenge ([http://localhost:5173/madrich/challenges/a194f6ea-0ad6-4816-873e-67db1c66b25f](http://localhost:5173/madrich/challenges/a194f6ea-0ad6-4816-873e-67db1c66b25f)) but there is no button to click done and return to the homepage after completion. Also, the page looks bare and needs branded styling.

I submitted Leo's reflection, but the Group Performance section of the admin homepage did not update ([http://localhost:5173/admin/home?program=12&group_type=classroom](http://localhost:5173/admin/home?program=12&group_type=classroom)).

[http://localhost:5173/admin/groups/192?tab=staff](http://localhost:5173/admin/groups/192?tab=staff) I can only see the names of the people in the groups, but I am not able to see their roles in the group. IN this case, I have Madrichim and Faculty listed in the same group. There should be pills next to each name telling me what their role is.

---



## 5. Profiles: subject (camper/student) and staff (madrich)

**Subject profile:** `SubjectDetail.jsx` (rebuilt in 8_6), reached from any group dashboard (`/dashboards/group/:id`). It's shared, uses `term()`, and works for students the same as campers.

Older camp-only subject views still exist alongside it:


| View                         | Route                            | Status                                                | Action                                                           |
| ---------------------------- | -------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------- |
| Unit Head camper dashboard   | `/unit-head/campers/:camperId`   | Older `CamperDashboard` component; hardcoded "Camper" | Redirect to the shared profile                                   |
| Camper Care camper dashboard | `/camper-care/campers/:camperId` | Older `CamperDashboard` plus Flag history             | Move Flag history into the shared profile as a section; redirect |
| Specialist camper view       | `/specialist/campers/:camperId`  | Own page, "My notes about this camper"                | Move "my notes" into the shared profile as a filter; redirect    |


**Staff profile:** a supervisor looking at one staff member's reflections. This also exists in several forms:


| View                           | Route                                                    | Who                                         |
| ------------------------------ | -------------------------------------------------------- | ------------------------------------------- |
| Faculty roster detail          | `/faculty/roster/:personId`                              | Faculty viewing a madrich ("Their entries") |
| LT member reflection           | `/leadership-team/teams/:teamRole/members/:membershipId` | LT viewing a staff member                   |
| Admin reflection member detail | `/admin/reflections/:role/members/:membershipId`         | Admin viewing a member                      |


**Verdict:** the subject profile is done; retire the three leftovers. The staff profile is the next "8_6" candidate: one staff profile page for all three entry points.

**Trips up a new admin / user:** *(Steve to fill in)*

---



## 6. Camp-only roles


| Role home              | Route            | What it is                                                    | Would a school want it?                                                                                                                                               |
| ---------------------- | ---------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Camper Care            | `/camper-care`   | Caseload, flagged campers, orders, my reflection; no `term()` | Maybe, as "student support" at a bigger school. Low priority                                                                                                          |
| Specialist             | `/specialist`    | Write a camper note (picker), my reflection, my recent notes  | Unlikely as is. Closest school analog is a specials teacher                                                                                                           |
| Kitchen / Housekeeping | `/kitchen-staff` | My reflection (today) + history, with a language selector     | **Yes, as a pattern.** It's a generic "staff who only self-reflect" home. A school's office or support staff would use exactly this. Rename the concept, not the page |
| Maintenance            | `/maintenance`   | Ticket queue                                                  | No                                                                                                                                                                    |


**Verdict:** leave these camp-only for now. The one worth generalizing is the kitchen-staff home, since every new customer will have some "just reflect" role.

---



## Suggested order

_Superseded by the Wave 10 queue in `migration_prompts/10_*` (bugs, roles and group types, TBE placement, forms visibility, then the homes). Kept for reference._

1. ~~Fix the TBE terminology mapping~~ (now part of 10_2b).
2. **Pair 1 (admin):** replace `orgSurfaces()` with per-org settings, make Program type a dropdown, run the school cards' wording through `term()`. This is the handoff surface.
3. **Pair 4 (counselor ↔ madrich):** add `term()` to the counselor home; bring the madrich home onto the 8_4 layout. TBE madrichim feel it weekly.
4. **Pair 3 (unit head ↔ faculty):** merge into one supervisor home.
5. **Pair 5:** retire the three old subject views; build one staff profile.
6. **Pairs 2 and 6:** decisions only, no build yet.



## Not covered by this pass

- Backend dashboard endpoints (`api/unit_head`, `api/faculty`, `api/director`, etc.) were mapped only through the frontend calls. Merging homes may mean merging or wrapping those endpoints too.
- The `/dashboards/*` camp analytics pages (Coverage, Concerns, Authors, Logs, Wellness) were listed but not broken down section by section.

