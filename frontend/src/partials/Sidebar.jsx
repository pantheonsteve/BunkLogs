import React, { useState, useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import isSuperAdmin from "../utils/auth/isSuperAdmin";
import { hasCapability } from "../utils/auth/capability";
import api from "../api";

import SidebarLinkGroup from "./SidebarLinkGroup";

import CampLogo from "../../src/images/clc-logo.jpeg";

// Legacy User.role values that can author a /reflect submission today.
// Re-derived via capability for the new sections; kept here only to
// preserve the existing top-level "Program reflection" / "My
// reflections" gates while we still trigger reflection assignments
// off legacy role.
const REFLECTION_FORM_ROLES = ['Counselor', 'Admin', 'Unit Head', 'Camper Care'];

// Capability shortcuts. SUPERVISOR_PLUS == "supervisor or stronger"
// because hasCapability(user, 'supervisor') is already inclusive of
// program_lead and admin (see capability.js docs). Listing them here
// keeps the JSX gate sites readable.
const SUPERVISOR_PLUS = ['supervisor'];
const PROGRAM_LEAD_PLUS = ['program_lead'];

/**
 * Navigation IA.
 *
 * The nav is role-dependent. There are three render paths:
 *
 *   1. maintenance-only members  — stripped nav (Maintenance + Observations)
 *   2. admins / super-admins     — curated Admin IA (see below)
 *   3. everyone else             — the shared default nav
 *
 * Admin IA (admin + super_admin) — Phase 1 of the role-based nav refactor:
 *
 *   HOME (top)           /admin/home
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
 *   ADMIN (collapsible, below Supervise)
 *     Admin dashboard     /admin/dashboard
 *     Templates           /admin/templates
 *     People              /admin/people
 *     Assignments         /admin/assignments
 *     Memberships         /admin/memberships
 *     Assignment groups   /admin/groups
 *     Field keys          /admin/field-keys
 *     Settings            /admin/settings
 *
 *   CRANE LAKE LEGACY (transitional)
 *     Bunk logs         /admin-bunk-logs
 *     Staff reflections /admin-dashboard
 *
 *   OTHER
 *     Orders            /orders
 *
 * Admins land on /admin (see pages/Dashboard.jsx). My tasks / File a
 * reflection / My reflections are folded into the Admin dashboard
 * rather than the global nav. The Leadership Team group is intentionally
 * absent from the Admin IA (it's the Leadership Team's own home).
 *
 * Default nav (non-admin): My work (Home/tasks/role-home/reflections/
 * observations/maintenance), Supervise (supervisor+; program_lead+ also
 * gets performance / log entries / reflections / authors there). Leadership
 * Team (program_lead+). Gates use hasCapability(user, [...]) ||
 * isSuperAdmin(user); direct `user.role` references remain only for
 * per-role workspace deep links and reflection-form access.
 *
 * Crane Lake legacy section disappears in wave 5 once
 * /admin-bunk-logs and /admin-dashboard are retired (see
 * migration_prompts/5_*).
 */
function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  variant = 'default',
}) {
  const location = useLocation();
  const { pathname } = location;
  const { user } = useAuth();

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
          className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out ${sidebarOpen ? "translate-x-0" : "-translate-x-64"} ${variant === 'v2' ? 'border-r border-gray-200 dark:border-gray-700/60' : 'rounded-r-2xl shadow-xs'}`}
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
  const canAdmin = hasCapability(user, 'admin') || isSuperAdmin(user);
  const canFileReflection = REFLECTION_FORM_ROLES.includes(user.role);
  const canSeeLogs = canSupervise || canAdmin;
  const canSeeReflectionsDashboard = canSeeLogs || canFileReflection;
  // Maintenance staff get a stripped-down nav: just the queue + notes. The
  // canonical role lives on Membership (legacy User.role has no maintenance
  // value), surfaced via `membership_roles` on the profile payload.
  const membershipRoles = Array.isArray(user.membership_roles) ? user.membership_roles : [];
  const isMaintenanceOnly =
    membershipRoles.includes('maintenance') &&
    !membershipRoles.includes('admin') &&
    !canAdmin;
  // Poll unread Observations count every 60 seconds (Step 7_23 nav badge).
  const [observationsUnread, setObservationsUnread] = useState(0);
  useEffect(() => {
    let cancelled = false;
    function fetchObsUnread() {
      api.get('/api/v1/observations/unread-count/').then(r => {
        if (!cancelled) setObservationsUnread(r.data.count ?? 0);
      }).catch(() => {});
    }
    fetchObsUnread();
    const id = setInterval(fetchObsUnread, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

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
        className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out ${sidebarOpen ? "translate-x-0" : "-translate-x-64"} ${variant === 'v2' ? 'border-r border-gray-200 dark:border-gray-700/60' : 'rounded-r-2xl shadow-xs'}`}
      >
        <SidebarHeader
          trigger={trigger}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
        />

        <div className="space-y-6">
          {isMaintenanceOnly ? (
            <Section heading="My work">
              <NavItem
                to="/maintenance"
                label="Maintenance Queue"
                icon={IconWrench}
              />
              <NavItem
                to="/observations"
                label="Observations"
                icon={IconChat}
                badge={observationsUnread > 0 ? observationsUnread : null}
              />
            </Section>
          ) : canAdmin ? (
          <>
          <div>
            <ul>
              <NavItem to="/admin/home" label="Home" icon={IconHome} end />
            </ul>
          </div>

          <Section heading="My work">
            <NavItem
              to="/groups/performance"
              label="Group Performance"
              icon={IconGrid}
            />
            <NavItem
              to="/dashboards/logs"
              label="Bunk Logs"
              icon={IconBars}
            />
            <NavItem
              to="/dashboards/reflections"
              label="Reflections"
              icon={IconClipboard}
            />
            <NavItem
              to="/observations"
              label="Observations"
              icon={IconChat}
              badge={observationsUnread > 0 ? observationsUnread : null}
            />
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
          </Section>

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

          <CollapsibleSection
            heading="Admin"
            activeWhen={
              pathname === '/admin' || pathname.startsWith('/admin/')
            }
            icon={IconGear}
            setSidebarExpanded={setSidebarExpanded}
          >
            <SubItem to="/admin/dashboard" label="Admin Dashboard" />
            <SubItem to="/admin/templates" label="Templates" />
            <SubItem to="/admin/people" label="People" />
            <SubItem to="/admin/assignments" label="Assignments" />
            <SubItem to="/admin/memberships" label="Memberships" />
            <SubItem to="/admin/groups" label="Assignment groups" />
            <SubItem to="/admin/field-keys" label="Field keys" />
            <SubItem to="/admin/settings" label="Settings" />
          </CollapsibleSection>

          <Section
            heading="Crane Lake legacy"
            headingTitle="Migrating to new schema in wave 5"
            data-testid="sidebar-legacy"
          >
            <NavItem
              to="/admin-bunk-logs"
              label="Bunk logs"
              icon={IconArchive}
            />
            <NavItem
              to="/admin-dashboard"
              label="Staff reflections"
              icon={IconArchive}
            />
          </Section>

          <Section heading="Other">
            <NavItem to="/orders" label="Orders" icon={IconReceipt} end />
          </Section>
          </>
          ) : (
          <>
          <Section heading="My work">
            <NavItem to="/dashboard" label="Home" icon={IconHome} end />
            <NavItem to="/tasks" label="My tasks" icon={IconTasks} />
            {user.role === 'Counselor' && (
              <NavItem
                to="/counselor"
                label="Counselor home"
                icon={IconCounselor}
              />
            )}
            {user.role === 'Unit Head' && (
              <NavItem
                to="/unit-head"
                label="Unit Head home"
                icon={IconCounselor}
              />
            )}
            {user.role === 'Camper Care' && (
              <NavItem
                to="/camper-care"
                label="Camper Care home"
                icon={IconHeart}
              />
            )}
            {canFileReflection && (
              <NavItem to="/reflect" label="File a reflection" icon={IconPencil} />
            )}
            {canFileReflection && (
              <NavItem to="/my-reflections" label="My reflections" icon={IconClipboard} />
            )}
            <NavItem
              to="/observations"
              label="Observations"
              icon={IconClipboard}
              badge={observationsUnread > 0 ? observationsUnread : null}
            />
            <NavItem
              to="/maintenance"
              label="Maintenance Queue"
              icon={IconWrench}
            />
            {canSupervise && !canSeeDashboards && canSeeLogs && (
              <>
                <NavItem
                  to="/groups/performance"
                  label="Group Performance"
                  icon={IconGrid}
                />
                <NavItem
                  to="/dashboards/logs"
                  label="Bunk Logs"
                  icon={IconBars}
                />
              </>
            )}
            {canSeeReflectionsDashboard && !canAdmin && (
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
              {canSeeDashboards && (
                <>
                  <NavItem
                    to="/dashboards/authors"
                    label="Author attribution"
                    icon={IconCounselor}
                  />
                  <NavItem
                    to="/dashboards/logs"
                    label="Bunk Logs"
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

          <Section heading="Other">
            <NavItem to="/orders" label="Orders" icon={IconReceipt} end />
          </Section>
          </>
          )}
        </div>

        {/* Expand / collapse button */}
        <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end mt-auto">
          <div className="w-12 pl-4 pr-3 py-2">
            <button
              className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400"
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
            >
              <span className="sr-only">Expand / collapse sidebar</span>
              <svg className="shrink-0 fill-current text-gray-400 dark:text-gray-500 sidebar-expanded:rotate-180" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                <path d="M15 16a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v14a1 1 0 0 1-1 1ZM8.586 7H1a1 1 0 1 0 0 2h7.586l-2.793 2.793a1 1 0 1 0 1.414 1.414l4.5-4.5A.997.997 0 0 0 12 8.01M11.924 7.617a.997.997 0 0 0-.217-.324l-4.5-4.5a1 1 0 0 0-1.414 1.414L8.586 7M12 7.99a.996.996 0 0 0-.076-.373Z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SidebarHeader({ trigger, sidebarOpen, setSidebarOpen }) {
  return (
    <div className="flex justify-between mb-10 pr-3 sm:px-2">
      <button
        ref={trigger}
        className="lg:hidden text-gray-500 hover:text-gray-400"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-controls="sidebar"
        aria-expanded={sidebarOpen}
      >
        <span className="sr-only">Close sidebar</span>
        <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M10.7 18.7l1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" />
        </svg>
      </button>
      <NavLink end to="/" className="block">
        <img className="shrink-0 mr-2 sm:mr-3" width="70" height="35" viewBox="0 0 36 36" src={CampLogo} />
      </NavLink>
    </div>
  );
}

function Section({ heading, headingTitle, children, ...rest }) {
  return (
    <div {...rest}>
      <h3
        className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3 mb-1"
        title={headingTitle}
      >
        <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">
          •••
        </span>
        <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">
          {heading}
        </span>
      </h3>
      <ul>{children}</ul>
    </div>
  );
}

function NavItem({ to, label, icon: Icon, end = false, badge = null }) {
  return (
    <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
      <NavLink
        end={end}
        to={to}
        className={({ isActive }) =>
          `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
            isActive ? "text-blue-600 dark:text-blue-400" : "hover:text-gray-900 dark:hover:text-white"
          }`
        }
      >
        <div className="flex items-center">
          <Icon />
          <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200 flex items-center gap-2">
            {label}
            {badge != null && (
              <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-violet-500 text-white text-xs font-bold leading-none">
                {badge}
              </span>
            )}
          </span>
        </div>
      </NavLink>
    </li>
  );
}

function CollapsibleSection({ heading, activeWhen, icon: Icon, setSidebarExpanded, children }) {
  return (
    <div>
      <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3 mb-1">
        <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">
          •••
        </span>
        <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">
          {heading}
        </span>
      </h3>
      <ul>
        <SidebarLinkGroup activecondition={activeWhen}>
          {(handleClick, open) => (
            <React.Fragment>
              <a
                href="#0"
                aria-expanded={open}
                className="block text-gray-800 dark:text-gray-100 truncate transition duration-150 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-lg"
                onClick={(e) => {
                  e.preventDefault();
                  handleClick();
                  setSidebarExpanded(true);
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Icon />
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                      {heading}
                    </span>
                  </div>
                  <div className="flex shrink-0 ml-2">
                    <svg
                      className={`w-3 h-3 shrink-0 ml-1 fill-current text-gray-400 dark:text-gray-500 ${open ? 'rotate-180' : ''}`}
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
              ? 'text-violet-600 dark:text-violet-400 font-medium'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
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

// === Icon components (kept inline to preserve the existing 24x24 stroke set) ===

function IconHome() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
  );
}
function IconTasks() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}
function IconCounselor() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  );
}
function IconHeart() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
    </svg>
  );
}
function IconPencil() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
    </svg>
  );
}
function IconClipboard() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
    </svg>
  );
}
function IconGrid() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
    </svg>
  );
}
function IconAlert() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
    </svg>
  );
}
function IconBars() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
    </svg>
  );
}
function IconGear() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}
function IconArchive() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
    </svg>
  );
}
function IconWrench() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" />
    </svg>
  );
}
function IconReceipt() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" />
    </svg>
  );
}

export default Sidebar;
