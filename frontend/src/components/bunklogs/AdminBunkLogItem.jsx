import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import GenericAvatar from '../../images/avatar-generic.png';

function AdminBunkLogItem({ log, date, onViewDetails }) {
  const [open, setOpen] = useState(false);

  // Score background color mapping - same as CamperLogsBunkViewItem
  const getScoreBackgroundColor = (score) => {
    if (!score) return "bg-gray-100";
    
    const scoreNum = parseInt(score);
    if (scoreNum == 1) return 'bg-[#e86946]';
    if (scoreNum == 2) return 'bg-[#de8d6f]';
    if (scoreNum == 3) return 'bg-[#e5e825]';
    if (scoreNum == 4) return 'bg-[#90d258]';
    if (scoreNum == 5) return 'bg-[#18d128]';
    return "bg-red-100";
  };

  // Help requested icon - same as CamperLogsBunkViewItem
  const getHelpRequestedIcon = (help_requested) => {
    if (help_requested === true) {
      return (
        <div className="flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="orange" className="size-6">
            <path d="M10.5 1.875a1.125 1.125 0 0 1 2.25 0v8.219c.517.162 1.02.382 1.5.659V3.375a1.125 1.125 0 0 1 2.25 0v10.937a4.505 4.505 0 0 0-3.25 2.373 8.963 8.963 0 0 1 4-.935A.75.75 0 0 0 18 15v-2.266a3.368 3.368 0 0 1 .988-2.37 1.125 1.125 0 0 1 1.591 1.59 1.118 1.118 0 0 0-.329.79v3.006h-.005a6 6 0 0 1-1.752 4.007l-1.736 1.736a6 6 0 0 1-4.242 1.757H10.5a7.5 7.5 0 0 1-7.5-7.5V6.375a1.125 1.125 0 0 1 2.25 0v5.519c.46-.452.965-.832 1.5-1.141V3.375a1.125 1.125 0 0 1 2.25 0v6.526c.495-.1.997-.151 1.5-.151V1.875Z" />
          </svg>
        </div>
      );
    }
    return null;
  };

  // Status indicator for not on camp
  const getNotOnCampIcon = (not_on_camp) => {
    if (not_on_camp === true) {
      return (
        <div className="flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="gray" className="size-6">
            <path fillRule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
          </svg>
        </div>
      );
    }
    return null;
  };

  return (
    <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
      <tr>
        {/* Camper Name */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <Link 
            to={`/camper/${log.camper_id}/${date}`}
            className="flex items-center text-gray-800 hover:text-blue-600 transition-colors"
          >
            <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-2 sm:mr-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {log.camper_first_name?.[0]}{log.camper_last_name?.[0]}
              </span>
            </div>
            <div className="font-medium text-gray-800 dark:text-gray-100 hover:text-blue-600 transition-colors">
              {log.camper_first_name} {log.camper_last_name}
            </div>
          </Link>
        </td>

        {/* Bunk/Unit */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">
            <div className="font-medium text-gray-800 dark:text-gray-100">{log.bunk_cabin_name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{log.unit_name || 'No unit'}</div>
          </div>
        </td>

        {/* Date */}
          <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
            <div className="text-center">
              {log.date ? (() => {
                // Parse as UTC to avoid timezone offset issues
                const [year, month, day] = log.date.split('-');
                const date = new Date(Date.UTC(year, month - 1, day));
                return date.toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric',
                  timeZone: 'UTC'
                });
              })() : ''}
            </div>
          </td>

          {/* Social Score */}
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(log.social_score)}`}>
          <div className="text-center">{log.social_score}</div>
        </td>

        {/* Behavioral Score */}
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(log.behavioral_score)}`}>
          <div className="text-center">{log.behavioral_score}</div>
        </td>

        {/* Participation Score */}
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(log.participation_score)}`}>
          <div className="text-center">{log.participation_score}</div>
        </td>

        {/* Not On Camp */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{getNotOnCampIcon(log.not_on_camp)}</div>
        </td>

        {/* Camper Care Help */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{getHelpRequestedIcon(log.camper_care_help_requested)}</div>
        </td>

        {/* Unit Head Help */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{getHelpRequestedIcon(log.unit_head_help_requested)}</div>
        </td>

        {/* Expand button */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap w-px">
          <div className="flex items-center">
            <button
              className={`text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400 ${open && 'rotate-180'}`}
              aria-expanded={open}
              onClick={() => setOpen(!open)}
              aria-controls={`description-${log.id}`}
            >
              <span className="sr-only">Menu</span>
              <svg className="w-8 h-8 fill-current" viewBox="0 0 32 32">
                <path d="M16 20l-5.4-5.4 1.4-1.4 4 4 4-4 1.4 1.4z" />
              </svg>
            </button>
          </div>
        </td>
      </tr>

      {/* Expandable details row */}
      <tr id={`description-${log.id}`} role="region" className={`${!open && 'hidden'}`}>
        <td colSpan="10" className="px-2 first:pl-5 last:pr-5 py-3">
          <div className="bg-gray-50 dark:bg-gray-950/[0.15] dark:text-gray-400 p-3 -mt-3">
            <div className="text-sm mb-3">
              <div className="mb-3">
                <strong>Description:</strong>
                <div className="mt-1" dangerouslySetInnerHTML={{ __html: log.description }}></div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Reporting Counselor:</strong>
                  <div className="mt-1">
                    {log.reporting_counselor_first_name && log.reporting_counselor_last_name ? (
                      <div>
                        {log.reporting_counselor_first_name} {log.reporting_counselor_last_name}
                        <div className="text-xs text-gray-500">{log.reporting_counselor_email}</div>
                      </div>
                    ) : (
                      <span className="text-gray-400">No counselor assigned</span>
                    )}
                  </div>
                </div>
                
                <div>
                  <strong>Created:</strong>
                  <div className="mt-1">
                    {new Date(log.created_at).toLocaleString('en-US', { 
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </div>
                </div>
              </div>

              {(log.not_on_camp || log.camper_care_help_requested || log.unit_head_help_requested) && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                  <strong>Status Flags:</strong>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {log.not_on_camp && (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full text-gray-600 bg-gray-100">
                        Not on camp
                      </span>
                    )}
                    {log.camper_care_help_requested && (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full text-red-600 bg-red-50">
                        Camper care help requested
                      </span>
                    )}
                    {log.unit_head_help_requested && (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full text-yellow-600 bg-yellow-50">
                        Unit head help requested
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  );
}

export default AdminBunkLogItem;
