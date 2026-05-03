import React, { useState, useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import SidebarLinkGroup from "./SidebarLinkGroup";

import CampLogo from "../../src/images/clc-logo.jpeg";

const REFLECTION_FORM_ROLES = ['Counselor', 'Admin', 'Unit Head', 'Camper Care'];

function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  variant = 'default',
  extraLinks = [], // <-- new prop for extra sidebar links
}) {
  const location = useLocation();
  const { pathname } = location;
  const { user } = useAuth();

  const trigger = useRef(null);
  const sidebar = useRef(null);

  const storedSidebarExpanded = localStorage.getItem("sidebar-expanded");
  const [sidebarExpanded, setSidebarExpanded] = useState(storedSidebarExpanded === null ? false : storedSidebarExpanded === "true");

  // close on click outside
  useEffect(() => {
    const clickHandler = ({ target }) => {
      if (!sidebar.current || !trigger.current) return;
      if (!sidebarOpen || sidebar.current.contains(target) || trigger.current.contains(target)) return;
      setSidebarOpen(false);
    };
    document.addEventListener("click", clickHandler);
    return () => document.removeEventListener("click", clickHandler);
  });

  // close if the esc key is pressed
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

  return (
    <div className="min-w-fit">
      {/* Sidebar backdrop (mobile only) */}
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        aria-hidden="true"
      ></div>

      {/* Sidebar */}
      <div
        id="sidebar"
        ref={sidebar}
        className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out ${sidebarOpen ? "translate-x-0" : "-translate-x-64"} ${variant === 'v2' ? 'border-r border-gray-200 dark:border-gray-700/60' : 'rounded-r-2xl shadow-xs'}`}
      >
        {/* Sidebar header */}
        <div className="flex justify-between mb-10 pr-3 sm:px-2">
          {/* Close button */}
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
          {/* Logo */}
          <NavLink end to="/" className="block">
            <img className="shrink-0 mr-2 sm:mr-3" width="70" height="35" viewBox="0 0 36 36" src={CampLogo} />
          </NavLink>
        </div>

        {/* Links */}
        <div className="space-y-8">
          {/* Pages group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">
                •••
              </span>
            </h3>
            <ul className="mt-3">
              {/* Role-specific dashboard links */}

              {user && user.role === 'Counselor' && (
                <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                  <NavLink 
                    to="/counselor-dashboard" 
                    className={({ isActive }) => 
                      `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                        isActive ? "text-blue-600 dark:text-blue-400" : "hover:text-gray-900 dark:hover:text-white"
                      }`
                    }
                  >
                    <div className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                      </svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                        My Reflections
                      </span>
                    </div>
                  </NavLink>
                </li>
              )}
              
              {user && user.role === 'Admin' && (
                <>
                  <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                    <NavLink 
                      to="/admin-bunk-logs" 
                      className={({ isActive }) => 
                        `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                          isActive ? "text-green-600 dark:text-green-400" : "hover:text-gray-900 dark:hover:text-white"
                        }`
                      }
                    >
                      <div className="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                        </svg>
                        <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                          Bunk Logs
                        </span>
                      </div>
                    </NavLink>
                  </li>
                  <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                    <NavLink 
                      to="/admin-dashboard" 
                      className={({ isActive }) => 
                        `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                          isActive ? "text-purple-600 dark:text-purple-400" : "hover:text-gray-900 dark:hover:text-white"
                        }`
                      }
                    >
                      <div className="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                        </svg>
                        <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                          Staff Reflections
                        </span>
                      </div>
                    </NavLink>
                  </li>
                </>
              )}
              {/* Camper Care extra links */}
              {user && user.role === 'Camper Care' && extraLinks && extraLinks.map(link => (
                <li key={link.label} className={`px-3 py-2 rounded-lg mb-0.5 last:mb-0 ${link.active ? 'bg-rose-50 dark:bg-rose-900/20' : ''}`}>
                  <button
                    className={`block w-full text-left text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                      link.active ? "text-rose-600 dark:text-rose-400 font-semibold" : "hover:text-gray-900 dark:hover:text-white"
                    }`}
                    onClick={link.onClick}
                  >
                    <div className="flex items-center">
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                        {link.label}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
              {user && ['Admin', 'Leadership'].includes(user.role) && (
                <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                  <NavLink
                    to="/team/dashboard"
                    className={({ isActive }) =>
                      `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                        isActive ? 'text-teal-600 dark:text-teal-400' : 'hover:text-gray-900 dark:hover:text-white'
                      }`
                    }
                  >
                    <div className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
                      </svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                        Unit health (LT)
                      </span>
                    </div>
                  </NavLink>
                </li>
              )}
              {user && ['Admin', 'Camper Care'].includes(user.role) && (
                <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                  <NavLink
                    to="/wellness/dashboard"
                    className={({ isActive }) =>
                      `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                        isActive ? 'text-teal-600 dark:text-teal-400' : 'hover:text-gray-900 dark:hover:text-white'
                      }`
                    }
                  >
                    <div className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                      </svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                        Wellness team
                      </span>
                    </div>
                  </NavLink>
                </li>
              )}
              {user && REFLECTION_FORM_ROLES.includes(user.role) && (
                <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                  <NavLink
                    to="/reflect"
                    className={({ isActive }) =>
                      `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                        isActive ? 'text-indigo-600 dark:text-indigo-400' : 'hover:text-gray-900 dark:hover:text-white'
                      }`
                    }
                  >
                    <div className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                      </svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                        Program reflection
                      </span>
                    </div>
                  </NavLink>
                </li>
              )}
              <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                <NavLink 
                  end 
                  to="/orders" 
                  className={({ isActive }) => 
                    `block text-gray-800 dark:text-gray-100 truncate transition duration-150 ${
                      isActive ? "text-blue-600 dark:text-blue-400" : "hover:text-gray-900 dark:hover:text-white"
                    }`
                  }
                >
                  <div className="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
                      Orders
                    </span>
                  </div>
                </NavLink>
              </li>              
            </ul>
          </div>
        </div>

        {/* Expand / collapse button */}
        <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end mt-auto">
          <div className="w-12 pl-4 pr-3 py-2">
            <button className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400" onClick={() => setSidebarExpanded(!sidebarExpanded)}>
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

export default Sidebar;
