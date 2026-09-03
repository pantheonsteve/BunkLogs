import UserMenu from '../DropdownProfile';
import ThemeToggle from '../ThemeToggle';

import GlobalSearch from './GlobalSearch';
import ProgramSwitcher from './ProgramSwitcher';

/**
 * One sticky bar for the admin: program in scope, search, then the
 * account controls.
 *
 * The admin used to stack the shared `Header` (theme + user menu) on top
 * of a second row holding the switcher and search -- two full-height
 * rules before any page content. This merges them. `Header` itself is
 * untouched because `AppLayout` and some seventy pages still mount it.
 */
export default function AdminTopBar({ sidebarOpen, setSidebarOpen }) {
  return (
    <header
      className="sticky top-0 z-30 bg-white/90 dark:bg-gray-800/90 backdrop-blur-md border-b border-gray-200 dark:border-gray-700/60"
      data-testid="admin-topbar"
    >
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3 h-16">
          <button
            className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden"
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
          <div className="hidden md:block min-w-0">
            <GlobalSearch />
          </div>

          <div className="ml-auto flex items-center gap-3">
            <ThemeToggle />
            <hr className="w-px h-6 bg-gray-200 dark:bg-gray-700/60 border-none" />
            <UserMenu align="right" />
          </div>
        </div>
      </div>
    </header>
  );
}
