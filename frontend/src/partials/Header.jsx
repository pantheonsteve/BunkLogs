import React from 'react';

import { useAuth } from '../auth/AuthContext';
import GlobalSearch from '../components/admin/GlobalSearch';
import ProgramSwitcher from '../components/admin/ProgramSwitcher';
import UserMenu from '../components/DropdownProfile';
import ThemeToggle from '../components/ThemeToggle';
import { useAdminProgram } from '../context/AdminProgramContext';
import { hasCapability } from '../utils/auth/capability';
import isSuperAdmin from '../utils/auth/isSuperAdmin';

/**
 * The one top bar for every signed-in page: program, search, today, then
 * the account controls.
 *
 * The program pill and the day counter read `AdminProgramContext`, so they
 * appear inside AdminLayout and stay hidden elsewhere -- non-admin users
 * have no program in frontend state yet. Search is the admin GlobalSearch,
 * shown to the same admin-style-nav users who could reach it before.
 */
function Header({ sidebarOpen, setSidebarOpen }) {
  const { user } = useAuth();
  const { program } = useAdminProgram();
  const canSearch = hasCapability(user, 'program_lead') || isSuperAdmin(user);

  return (
    <header
      className="sticky top-0 z-30 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-line"
      data-testid="app-header"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 min-h-16 py-3 px-4 sm:px-6 lg:px-8">
        <button
          className="text-muted hover:text-ink lg:hidden"
          aria-controls="sidebar"
          aria-expanded={sidebarOpen}
          onClick={(e) => { e.stopPropagation(); setSidebarOpen(!sidebarOpen); }}
        >
          <span className="sr-only">Open sidebar</span>
          <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="5" width="16" height="2" />
            <rect x="4" y="11" width="16" height="2" />
            <rect x="4" y="17" width="16" height="2" />
          </svg>
        </button>

        <ProgramSwitcher />

        {canSearch && (
          <div className="order-last basis-full md:order-none md:basis-0 md:flex-1 md:max-w-md min-w-0">
            <GlobalSearch />
          </div>
        )}

        <div className="ml-auto flex items-center gap-3">
          <TodayLabel program={program} />
          <ThemeToggle />
          <UserMenu align="right" />
        </div>
      </div>
    </header>
  );
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** 'YYYY-MM-DD' as a UTC day number, so DST can't shift the count. */
function dayNumber(ymd) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(ymd || ''));
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) / DAY_MS : null;
}

/** "Day N of M" while today falls inside the program, else null. */
export function programDayLabel(program, today = new Date()) {
  const start = dayNumber(program?.start_date);
  const end = dayNumber(program?.end_date);
  if (start == null || end == null || end < start) return null;
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) / DAY_MS;
  if (now < start || now > end) return null;
  return `Day ${now - start + 1} of ${end - start + 1}`;
}

function TodayLabel({ program }) {
  const today = new Date();
  const date = today.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const day = programDayLabel(program, today);
  return (
    <span className="text-[13px] text-ink-2 whitespace-nowrap" data-testid="header-today">
      {day ? (
        <>
          <span className="hidden sm:inline">{date} · </span>
          {day}
        </>
      ) : (
        date
      )}
    </span>
  );
}

export default Header;
