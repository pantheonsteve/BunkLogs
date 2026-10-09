import React, { Children, useState, useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  ChartColumn,
  ChartPie,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  ClipboardList,
  Heart,
  House,
  LayoutDashboard,
  LayoutGrid,
  MessageSquare,
  PenLine,
  Rows3,
  Settings,
  SlidersHorizontal,
  UserPen,
  Users,
  Wrench,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import isSuperAdmin from "../utils/auth/isSuperAdmin";
import {
  hasCapability,
  homePathForUser,
  isMaintenanceOnlyMember,
  membershipRolesForUser,
} from "../utils/auth/capability";
import { orgSurfaces } from "../utils/auth/orgProfile";
import api from "../api";

import SidebarLinkGroup from "./SidebarLinkGroup";
import Badge from "../components/ui/Badge";
import { OrgLogo } from "../components/OrgBrandingAssets";
import { useOrgBranding, useTerm } from "../context/OrgBrandingContext";
import { adminNavItems, leadershipNavItems } from "./adminNavConfig";

// Membership roles that can author a /reflect submission today; kept to
// preserve the existing top-level "Program reflection" / "My reflections"
// gates.
const REFLECTION_FORM_ROLES = [
  'counselor', 'junior_counselor', 'general_counselor',
  'admin', 'unit_head', 'faculty',
  'camper_care', 'health_center', 'medical', 'special_diets',
];

// Roles that file or answer a reflection of their own. Admin alone does
// not: the Director answers questions, which is a separate count.
const PERSONAL_REFLECTION_ROLES = [
  'counselor', 'junior_counselor', 'general_counselor',
  'unit_head', 'faculty', 'madrich',
  'camper_care', 'health_center', 'medical', 'special_diets',
];

// Shared layout classes for the lg–xl icon-only sidebar (expanded at 2xl+ or via toggle).
const SIDEBAR_SHELL =
  'flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-[4.5rem] lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-900 border-r border-line px-3.5 py-5 lg:px-2 lg:sidebar-expanded:px-3.5 2xl:px-3.5 transition-all duration-200 ease-in-out';
const COLLAPSED_ICON_ROW =
  'flex items-center lg:justify-center lg:sidebar-expanded:justify-start 2xl:justify-start';
const COLLAPSED_LABEL =
  'inline-flex items-center ml-3 lg:ml-0 lg:sidebar-expanded:ml-3 2xl:ml-3 lg:hidden lg:sidebar-expanded:inline-flex 2xl:inline-flex duration-200';
const COLLAPSED_SECTION_RULE =
  'hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden border-t border-line mx-1 mb-3';
const COLLAPSED_SECTION_HEADING =
  'lg:hidden lg:sidebar-expanded:block 2xl:block';
const SECTION_HEADING =
  'text-[11px] font-semibold uppercase tracking-wider text-muted px-2.5 pb-1.5';
const ICON_PROPS = { size: 18, strokeWidth: 1.8, 'aria-hidden': true, className: 'shrink-0' };

const COUNSELOR_ROLES = ['counselor', 'junior_counselor', 'general_counselor'];
const CAMPER_CARE_ROLES = ['camper_care', 'health_center', 'medical', 'special_diets'];

// Capability shortcuts. SUPERVISOR_PLUS == "supervisor or stronger"
// because hasCapability(user, 'supervisor') is already inclusive of
// program_lead and admin (see capability.js docs). Listing them here
// keeps the JSX gate sites readable.
const SUPERVISOR_PLUS = ['supervisor'];
const PROGRAM_LEAD_PLUS = ['program_lead'];

/**
 * Navigation IA.
 *
 * The nav is role-dependent. There are four render paths:
 *
 *   1. maintenance-only members  — Maintenance Queue only
 *   2. admins / super-admins     — curated Admin IA (see below)
 *   3. program_lead (LT)         — same Admin IA structure; Home →
 *      /leadership-team; Admin submenu is Templates only
 *   4. everyone else             — the shared default nav
 *
 * Admin IA (admin + super_admin) — Phase 1 of the role-based nav refactor:
 *
 *   HOME (top)           /admin/home
 *   HELP (top)           /help
 *
 *   MY WORK
 *     Performance Dashboard /groups/performance
 *     Log Entries         /dashboards/logs
 *     Reflections         /dashboards/reflections
 *     Observations      /observations
 *     Maintenance Queue /maintenance
 *     Camper Care orders /camper-care/orders
 *
 *   SUPERVISE
 *     Coverage dashboard  /dashboards/coverage
 *     Concerns inbox    /dashboards/concerns
 *     Author attribution /dashboards/authors
 *
 *   ADMIN (collapsible, below Supervise) — see partials/adminNavConfig.js
 *     People / Groups, then Forms, Reports and Setup sub-groups. Groups
 *     is labelled per-tenant ("Classes" for TBE). Which reports appear
 *     depends on the org's surfaces.
 *
 * Admins land on /admin (see pages/Dashboard.jsx). Leadership Team lands
 * on /leadership-team with the same My work / Supervise sections but
 * only Templates under Admin. My tasks / File a reflection / My
 * reflections are folded into those home dashboards, not the global nav.
 *
 * Default nav (non-admin, non-LT): an unheaded Home (+ Help for
 * program_lead+), My work (tasks/reflections/observations/maintenance),
 * Supervise (supervisor+). Camper Care omits My tasks / File a reflection /
 * My reflections / Daily logs — those live on the Camper Care home dashboard.
 * Camper Care also gets Flagged campers + Camper Care orders in the global
 * nav (dashboard cards remain secondary entry points with counts).
 * Gates use
 * hasCapability(user, [...]) || isSuperAdmin(user); membership roles (from
 * the per-org auth payload) drive reflection-form access. Role workspaces
 * are the Home link target (no duplicate "Counselor home" entries).
 */
function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  navBadges = null,
}) {
  const location = useLocation();
  const { pathname } = location;
  const { user } = useAuth();
  const term = useTerm();

  const trigger = useRef(null);
  const sidebar = useRef(null);

  const storedSidebarExpanded = localStorage.getItem("sidebar-expanded");
  const [sidebarExpanded, setSidebarExpanded] = useState(storedSidebarExpanded === null ? false : storedSidebarExpanded === "true");

  useEffect(() => {
    const clickHandler = ({ target }) => {
      if (!sidebar.current || !trigger.current) return;
      if (!sidebarOpen || sidebar.current.contains(target) || trigger.current.contains(target)) return;
      setSidebarOpen(false);
    };
    document.addEventListener("click", clickHandler);
    return () => document.removeEventListener("click", clickHandler);
  });

  useEffect(() => {
    const keyHandler = ({ keyCode }) => {
      if (!sidebarOpen || keyCode !== 27) return;
      setSidebarOpen(false);
    };
    document.addEventListener("keydown", keyHandler);
    return () => document.removeEventListener("keydown", keyHandler);
  });

  useEffect(() => {
    localStorage.setItem("sidebar-expanded", sidebarExpanded);
    if (sidebarExpanded) {
      document.querySelector("body").classList.add("sidebar-expanded");
    } else {
      document.querySelector("body").classList.remove("sidebar-expanded");
    }
  }, [sidebarExpanded]);

  if (!user) {
    // Render the chrome with no link sections; pages that mount the
    // Sidebar before auth resolves keep their layout.
    return (
      <div className="min-w-fit">
        <div
          className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${
            sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
          aria-hidden="true"
        ></div>
        <div
          id="sidebar"
          ref={sidebar}
          className={`${SIDEBAR_SHELL} ${sidebarOpen ? "translate-x-0" : "-translate-x-64"}`}
        >
          <SidebarHeader
            trigger={trigger}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        </div>
      </div>
    );
  }

  const canSupervise = hasCapability(user, SUPERVISOR_PLUS) || isSuperAdmin(user);
  const canSeeDashboards = hasCapability(user, PROGRAM_LEAD_PLUS) || isSuperAdmin(user);
  const canSeeLeadershipTeam = hasCapability(user, PROGRAM_LEAD_PLUS) || isSuperAdmin(user);
  const canSeeHelp = canSeeLeadershipTeam;
  const canAdmin = hasCapability(user, 'admin') || isSuperAdmin(user);
  const useLeadershipAdminNav = canSeeDashboards && !canAdmin;
  const useAdminStyleNav = canAdmin || useLeadershipAdminNav;
  const adminStyleHomePath = canAdmin ? '/admin/home' : '/leadership-team';
  const membershipRoles = membershipRolesForUser(user);
  const canFileReflection = REFLECTION_FORM_ROLES.some((r) => membershipRoles.includes(r));
  const isCounselor = COUNSELOR_ROLES.some((r) => membershipRoles.includes(r));
  const isUnitHead = membershipRoles.includes('unit_head');
  const isCamperCare = CAMPER_CARE_ROLES.some((r) => membershipRoles.includes(r));
  const canSeeFileReflectionNav = canFileReflection && !isCounselor && !isCamperCare && !isUnitHead;
  const canSeeLogs = canSupervise || canAdmin;
  // Counselors see assigned/submitted work via My tasks + My reflections, not the org-wide dashboard.
  const canSeeReflectionsDashboard = (canSeeLogs || canFileReflection) && !isCounselor;
  // Maintenance staff get a stripped-down nav: just the queue. The canonical
  // role lives on Membership (legacy User.role has no maintenance value),
  // surfaced via `membership_roles` on the profile payload.
  const isMaintenanceOnly = isMaintenanceOnlyMember(user);
  const isMadrich = membershipRoles.includes('madrich');
  const isFaculty = membershipRoles.includes('faculty');
  const homePath = homePathForUser(user);
  // Which product surfaces this tenant gets (camp vs religious school).
  const surfaces = orgSurfaces(user);
  const adminNav = canAdmin ? adminNavItems(surfaces, term) : leadershipNavItems();
  const hasReflectionWork = PERSONAL_REFLECTION_ROLES.some((role) => membershipRoles.includes(role))
    || (navBadges?.questionsForYou > 0);
  const setupProgress = navBadges?.setupProgress;
  const setupIncomplete = !setupProgress || setupProgress.done < setupProgress.total;
  // Poll unread Observations count every 60 seconds (Step 7_23 nav badge).
  const [observationsUnread, setObservationsUnread] = useState(0);
  const pollObservations = surfaces.observations;
  useEffect(() => {
    if (!pollObservations) return undefined;
    let cancelled = false;
    function fetchObsUnread() {
      api.get('/api/v1/observations/unread-count/').then(r => {
        if (!cancelled) setObservationsUnread(r.data.count ?? 0);
      }).catch(() => {});
    }
    fetchObsUnread();
    const id = setInterval(fetchObsUnread, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, [pollObservations]);

  return (
    <div className="min-w-fit">
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        aria-hidden="true"
      ></div>

      <div
        id="sidebar"
        ref={sidebar}
        className={`${SIDEBAR_SHELL} ${sidebarOpen ? "translate-x-0" : "-translate-x-64"}`}
      >
        <SidebarHeader
          trigger={trigger}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          homePath={homePath}
        />

        <div className="flex flex-1 flex-col space-y-6">
          {isMaintenanceOnly ? (
            <Section>
              <NavItem
                to="/maintenance"
                label="Maintenance Queue"
                icon={IconWrench}
              />
            </Section>
          ) : useAdminStyleNav ? (
          <>
          <Section>
            {/* Admins reach their home through the Admin section's
                Dashboard item; a second Home row up here just pointed
                at the same page. */}
            <NavItem
              to={canAdmin ? '/admin/home' : adminStyleHomePath}
              label="Home"
              icon={IconHome}
              end
            />
            {!canAdmin && canSeeHelp && (
              <NavItem to="/help" label="Help" icon={IconHelp} />
            )}
          </Section>

          {(hasReflectionWork || surfaces.campDashboards || surfaces.observations || surfaces.campOps) && (
          <Section heading="My work">
            {surfaces.campDashboards && (
              <>
                <NavItem
                  to="/groups/performance"
                  label="Group Performance"
                  icon={IconGrid}
                />
                {/* Not "Bunk Logs" — that's the product's name, and a nav
                    item wearing it makes every other page look like it
                    isn't part of the product. */}
                <NavItem
                  to="/dashboards/logs"
                  label="Daily logs"
                  icon={IconBars}
                />
              </>
            )}
            {surfaces.campDashboards && canSeeReflectionsDashboard && (
              <NavItem
                to="/dashboards/reflections"
                label="Reflections"
                icon={IconClipboard}
              />
            )}
            {!surfaces.campDashboards && hasReflectionWork && (
              <NavItem
                to="/admin/reflections"
                label="Reflections"
                icon={IconClipboard}
              />
            )}
            {surfaces.observations && (
              <NavItem
                to="/observations"
                label="Observations"
                icon={IconChat}
                badge={observationsUnread > 0 ? observationsUnread : null}
              />
            )}
            {surfaces.campOps && (
              <>
                <NavItem
                  to="/maintenance"
                  label="Maintenance Queue"
                  icon={IconWrench}
                />
                <NavItem
                  to="/camper-care/orders"
                  label="Camper Care orders"
                  icon={IconHeart}
                />
              </>
            )}
          </Section>
          )}

          {surfaces.campDashboards && (
            <Section heading="Supervise">
              <NavItem
                to="/dashboards/coverage"
                label="Coverage dashboard"
                icon={IconGrid}
              />
              <NavItem
                to="/dashboards/concerns"
                label="Concerns inbox"
                icon={IconAlert}
              />
              <NavItem
                to="/dashboards/authors"
                label="Author attribution"
                icon={IconCounselor}
              />
            </Section>
          )}

          <Section heading={canAdmin ? 'Manage' : 'Admin'}>
            {(canAdmin ? adminNav.filter((item) => item.placement !== 'footer' && item.placement !== 'home') : adminNav).map((item) => {
              const count = badgeCount(navBadges, item.badge);
              return (
                <NavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={ADMIN_NAV_ICONS[item.icon] || IconClipboard}
                  end={item.end}
                  badge={count}
                  badgeLabel={count != null && item.badgeNoun ? `${count} ${item.badgeNoun}` : null}
                />
              );
            })}
          </Section>
          {canAdmin && (
            <div className="mt-auto pt-4 border-t border-line">
              <ul className="space-y-0.5">
                {adminNav.filter((item) => item.placement === 'footer' && (item.to !== '/admin/setup' || setupIncomplete)).map((item) => {
                  const progress = item.to === '/admin/setup' && setupProgress && setupIncomplete
                    ? `${setupProgress.done}/${setupProgress.total}`
                    : null;
                  return (
                    <NavItem
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      icon={ADMIN_NAV_ICONS[item.icon]}
                      badge={progress}
                      badgeTone="warn"
                      badgeLabel={progress ? `${progress} setup steps complete` : null}
                    />
                  );
                })}
                {canSeeHelp && (
                  <NavItem to="/help" label="Help" icon={IconHelp} />
                )}
              </ul>
            </div>
          )}
          </>
          ) : (
          <>
          <Section>
            <NavItem to={homePath} label="Home" icon={IconHome} end />
            {canSeeHelp && (
              <NavItem to="/help" label="Help" icon={IconHelp} />
            )}
          </Section>

          <Section heading="My work">
            {isCamperCare && (
              <>
                <NavItem to="/camper-care/flags" label="Flagged campers" icon={IconAlert} />
                <NavItem to="/camper-care/orders" label="Camper Care orders" icon={IconHeart} />
              </>
            )}
            {!isCamperCare && (
              <NavItem to="/tasks" label="My tasks" icon={IconTasks} />
            )}
            {canSeeFileReflectionNav && (
              <NavItem to="/reflect" label="File a reflection" icon={IconPencil} />
            )}
            {canFileReflection && !isCamperCare && (
              <NavItem to="/my-reflections" label="My reflections" icon={IconClipboard} />
            )}
            {isMadrich && (
              <NavItem to="/madrich/history" label="My reflections" icon={IconClipboard} />
            )}
            {isFaculty && (
              <NavItem to="/faculty/challenges" label="Challenges" icon={IconAlert} />
            )}
            {surfaces.observations && (
              <NavItem
                to="/observations"
                label="Observations"
                icon={IconClipboard}
                badge={observationsUnread > 0 ? observationsUnread : null}
              />
            )}
            {surfaces.campOps && (
              <NavItem
                to="/maintenance"
                label="Maintenance Queue"
                icon={IconWrench}
              />
            )}
            {canSupervise && !canSeeDashboards && !isUnitHead && (
              <NavItem
                to="/groups/performance"
                label="Group Performance"
                icon={IconGrid}
              />
            )}
            {canSupervise && !canSeeDashboards && canSeeLogs && !isCamperCare && !isUnitHead && (
              <NavItem
                to="/dashboards/logs"
                label="Daily logs"
                icon={IconBars}
              />
            )}
            {canSeeReflectionsDashboard && !canAdmin && !isUnitHead && (
              <NavItem
                to="/dashboards/reflections"
                label="Reflections"
                icon={IconClipboard}
              />
            )}
          </Section>

          {canSupervise && (
            <Section heading="Supervise">
              {canSeeDashboards && (
                <NavItem
                  to="/groups/performance"
                  label="Performance Dashboard"
                  icon={IconGrid}
                />
              )}
              <NavItem
                to="/dashboards/coverage"
                label="Coverage dashboard"
                icon={IconGrid}
              />
              <NavItem
                to="/dashboards/concerns"
                label="Concerns about my unit"
                icon={IconAlert}
              />
              {isUnitHead && (
                <NavItem
                  to="/unit-head/staff-reflections"
                  label="Staff Reflections"
                  icon={IconClipboard}
                />
              )}
              {canSeeDashboards && (
                <>
                  <NavItem
                    to="/dashboards/authors"
                    label="Author attribution"
                    icon={IconCounselor}
                  />
                  <NavItem
                    to="/dashboards/logs"
                    label="Daily logs"
                    icon={IconBars}
                  />
                  <NavItem
                    to="/dashboards/reflections"
                    label="Reflections"
                    icon={IconClipboard}
                  />
                </>
              )}
            </Section>
          )}

          {canSeeLeadershipTeam && (
            <CollapsibleSection
              heading="Leadership Team"
              activeWhen={
                pathname === '/leadership-team' || pathname.startsWith('/leadership-team/')
              }
              icon={IconGrid}
              setSidebarExpanded={setSidebarExpanded}
            >
              <SubItem to="/leadership-team" label="Overview" end />
              <SubItem to="/leadership-team/self-reflection" label="My reflection" />
            </CollapsibleSection>
          )}
          </>
          )}
        </div>

        {/* Expand / collapse button */}
        <div className="pt-3 hidden lg:flex 2xl:hidden justify-center lg:sidebar-expanded:justify-end mt-auto">
          <div className="w-full lg:w-auto pl-0 lg:sidebar-expanded:pl-4 pr-0 lg:sidebar-expanded:pr-3 py-2 flex justify-center lg:sidebar-expanded:block">
            <button
              className="text-muted hover:text-ink p-1"
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
            >
              <span className="sr-only">Expand / collapse sidebar</span>
              <svg className="shrink-0 fill-current sidebar-expanded:rotate-180" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                <path d="M15 16a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v14a1 1 0 0 1-1 1ZM8.586 7H1a1 1 0 1 0 0 2h7.586l-2.793 2.793a1 1 0 1 0 1.414 1.414l4.5-4.5A.997.997 0 0 0 12 8.01M11.924 7.617a.997.997 0 0 0-.217-.324l-4.5-4.5a1 1 0 0 0-1.414 1.414L8.586 7M12 7.99a.996.996 0 0 0-.076-.373Z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SidebarHeader({ trigger, sidebarOpen, setSidebarOpen, homePath = '/' }) {
  const [logoFailed, setLogoFailed] = useState(false);
  return (
    <div className="flex justify-between mb-8 lg:mb-4 lg:sidebar-expanded:mb-8 2xl:mb-8 pr-3 sm:px-1.5 lg:pr-0 lg:justify-center lg:sidebar-expanded:justify-between 2xl:justify-between lg:sidebar-expanded:pr-3 2xl:pr-3">
      <button
        ref={trigger}
        className="lg:hidden text-muted hover:text-ink"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-controls="sidebar"
        aria-expanded={sidebarOpen}
      >
        <span className="sr-only">Close sidebar</span>
        <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M10.7 18.7l1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" />
        </svg>
      </button>
      <div className="min-w-0 w-full max-w-full flex-1 lg:flex-none lg:w-full">
        <OrgLogo to={homePath} variant="sidebar" onLoadError={() => setLogoFailed(true)} />
        {logoFailed ? null : <Wordmark />}
      </div>
    </div>
  );
}

/**
 * Product name over org name, under the mark. Hidden while the sidebar is
 * icon-only, where there is no room for two lines of text.
 */
function Wordmark() {
  const { productName, displayName, logoUrl, isClc } = useOrgBranding();
  // With no mark to show, OrgLogo already renders the org name as text —
  // repeating it directly underneath reads as a rendering bug.
  if (!logoUrl && !isClc) return null;
  if (!displayName || displayName === productName) return null;
  return (
    <div className="mt-2.5 px-1.5 min-w-0 lg:hidden lg:sidebar-expanded:block 2xl:block">
      <div className="text-[15px] font-bold leading-tight text-ink truncate">
        {productName}
      </div>
      <div className="text-xs leading-snug text-muted truncate">
        {displayName}
      </div>
    </div>
  );
}

/** A nav group. The first group on every path goes unheaded, per the mockup. */
function Section({ heading = null, children }) {
  if (Children.toArray(children).length === 0) return null;
  return (
    <div>
      {heading && (
        <>
          <div className={COLLAPSED_SECTION_RULE} aria-hidden="true" />
          <h3 className={`${SECTION_HEADING} ${COLLAPSED_SECTION_HEADING}`}>{heading}</h3>
        </>
      )}
      <ul className="space-y-0.5">{children}</ul>
    </div>
  );
}

const NAV_ITEM_BASE =
  'flex items-center min-h-10 px-2.5 lg:px-2 lg:sidebar-expanded:px-2.5 2xl:px-2.5 text-sm rounded-lg transition duration-150';
const NAV_ITEM_ACTIVE =
  'bg-brand-soft text-violet-800 dark:text-violet-200 font-semibold';
const NAV_ITEM_IDLE =
  'font-medium text-[#3a3850] dark:text-gray-300 hover:bg-line-soft hover:text-ink';
const COLLAPSED_DOT_TONE = { danger: 'bg-danger-ink', warn: 'bg-warn-ink' };

function NavItem({
  to,
  label,
  icon: Icon,
  end = false,
  badge = null,
  badgeLabel = null,
  badgeTone = 'danger',
}) {
  return (
    <li>
      <NavLink
        end={end}
        to={to}
        title={label}
        className={({ isActive }) =>
          `${NAV_ITEM_BASE} ${isActive ? NAV_ITEM_ACTIVE : NAV_ITEM_IDLE}`
        }
      >
        <div className={`${COLLAPSED_ICON_ROW} relative w-full`}>
          <Icon {...ICON_PROPS} />
          <span className={`${COLLAPSED_LABEL} flex-1 min-w-0 gap-2`}>
            <span className="truncate">{label}</span>
            {badge != null && (
              <Badge
                tone={badgeTone}
                size="sm"
                className="ml-auto shrink-0 font-semibold"
                aria-label={badgeLabel || undefined}
              >
                {badge}
              </Badge>
            )}
          </span>
          {badge != null && (
            <span
              className={`hidden lg:flex lg:sidebar-expanded:hidden 2xl:hidden absolute -top-0.5 right-0.5 h-2 w-2 rounded-full ${COLLAPSED_DOT_TONE[badgeTone] || COLLAPSED_DOT_TONE.danger}`}
              aria-label={`${badge} need attention`}
            />
          )}
        </div>
      </NavLink>
    </li>
  );
}

function CollapsibleSection({ heading, activeWhen, icon: Icon, setSidebarExpanded, children }) {
  return (
    <div>
      <div className={COLLAPSED_SECTION_RULE} aria-hidden="true" />
      <h3 className={`${SECTION_HEADING} ${COLLAPSED_SECTION_HEADING}`}>
        {heading}
      </h3>
      <ul>
        <SidebarLinkGroup activecondition={activeWhen}>
          {(handleClick, open) => (
            <React.Fragment>
              <a
                href="#0"
                aria-expanded={open}
                title={heading}
                className="flex items-center min-h-10 text-sm font-medium text-[#3a3850] dark:text-gray-300 transition duration-150 hover:text-ink px-2.5 rounded-lg lg:px-0 lg:sidebar-expanded:px-2.5 2xl:px-2.5"
                onClick={(e) => {
                  e.preventDefault();
                  handleClick();
                  setSidebarExpanded(true);
                }}
              >
                <div className="flex w-full items-center justify-between lg:justify-center lg:sidebar-expanded:justify-between 2xl:justify-between">
                  <div className={COLLAPSED_ICON_ROW}>
                    <Icon {...ICON_PROPS} />
                    <span className={COLLAPSED_LABEL}>
                      {heading}
                    </span>
                  </div>
                  <div className="flex shrink-0 ml-2 lg:hidden lg:sidebar-expanded:block 2xl:block">
                    <svg
                      className={`w-3 h-3 shrink-0 ml-1 fill-current text-muted ${open ? 'rotate-180' : ''}`}
                      viewBox="0 0 12 12"
                      aria-hidden="true"
                    >
                      <path d="M5.9 11.4L.5 6l1.4-1.4 4 4 4-4L11.3 6z" />
                    </svg>
                  </div>
                </div>
              </a>
              <div className="lg:hidden lg:sidebar-expanded:block 2xl:block">
                <ul className={`pl-9 mt-1 ${!open ? 'hidden' : ''}`}>
                  {children}
                </ul>
              </div>
            </React.Fragment>
          )}
        </SidebarLinkGroup>
      </ul>
    </div>
  );
}

function SubItem({ to, label, end = false }) {
  return (
    <li className="mb-1 last:mb-0">
      <NavLink
        end={end}
        to={to}
        className={({ isActive }) =>
          `block transition duration-150 truncate ${
            isActive
              ? 'text-violet-800 dark:text-violet-200 font-semibold'
              : 'text-muted hover:text-ink'
          }`
        }
      >
        <span className="text-sm lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
          {label}
        </span>
      </NavLink>
    </li>
  );
}

const IconHome = House;
const IconTasks = CircleCheck;
const IconCounselor = UserPen;
const IconHeart = Heart;
const IconPencil = PenLine;
const IconClipboard = ClipboardList;
const IconChat = MessageSquare;
const IconGrid = LayoutGrid;
const IconAlert = CircleAlert;
const IconBars = ChartColumn;
const IconWrench = Wrench;
const IconHelp = CircleHelp;

const ADMIN_NAV_ICONS = {
  dashboard: LayoutDashboard,
  people: Users,
  groups: Rows3,
  forms: PenLine,
  reports: ChartPie,
  setup: SlidersHorizontal,
  settings: Settings,
};

/** A badge only earns space when there is something to act on. */
function badgeCount(navBadges, key) {
  if (!key || !navBadges) return null;
  const n = navBadges[key];
  return typeof n === 'number' && n > 0 ? n : null;
}

export default Sidebar;
