import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import GenericAvatar from '../../images/avatar-generic.png';

function CamperCareBunkLogItem(props) {
  // Score background color mapping
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

  // Big Green Check if camper care help is requested
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

  const [open, setOpen] = useState(false);

  return (
    <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
      <tr>
        {/* Camper Name - WITH LINK for Camper Care users */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
          <Link className="font-medium text-gray-800 dark:text-gray-100" to={`/camper/${props.camper_id}/${props.date}`}>
            <div className="flex items-center text-gray-800">
              <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-2 sm:mr-3">
                <img className="rounded-full ml-1" src={props.image ? props.image : GenericAvatar} width="40" height="40" alt={`${props.camper_first_name} ${props.camper_last_name}`} />
              </div>
              <div>
                <div className="font-medium text-gray-800 dark:text-gray-100">
                  {props.camper_first_name} {props.camper_last_name}
                </div>
              </div>
            </div>
          </Link>
        </td>
        {/* Bunk/Unit column */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
          <div className="text-center">
            <div className="font-medium text-gray-800 dark:text-gray-100">{props.bunk_name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{props.unit_name || 'No unit'}</div>
          </div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
          <div className="text-center">{props.date}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.social_score)}`}> 
          <div className="text-center">{props.social_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.participation_score)}`}> 
          <div className="text-center">{props.participation_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.behavior_score)}`}> 
          <div className="text-center">{props.behavior_score}</div>
        </td>
        {/* Description column - always visible */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-pre-line max-w-xs break-words align-top align-center border border-gray-300 dark:border-gray-700">
          <div className="text-gray-700 dark:text-gray-200 text-sm" style={{ whiteSpace: 'pre-line' }}>
            {/* Status badges for help requests */}
            <div className="flex flex-wrap gap-2 mb-2">
              {props.camper_care_help && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full text-red-700 bg-red-100 border border-red-200">
                  <svg className="w-3 h-3 mr-1 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path d="M18 13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v6zm-1-6H3v6h14V7zm-7 2a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1z"/></svg>
                  Camper Care Help
                </span>
              )}
              {props.unit_head_help && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full text-yellow-800 bg-yellow-100 border border-yellow-200">
                  <svg className="w-3 h-3 mr-1 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm1 12H9v-2h2v2zm0-4H9V6h2v4z"/></svg>
                  Unit Head Help
                </span>
              )}
            </div>
            <div>
              {props.description ? (
                props.description.includes('<') ? (
                  <span dangerouslySetInnerHTML={{ __html: props.description }} />
                ) : (
                  props.description
                )
              ) : (
                <span className="text-gray-400">No description</span>
              )}
            </div>
            <div className="mt-2 text-xs text-gray-500">
              <strong>Reporting Counselor:</strong>{' '}
              {props.counselor_first_name && props.counselor_last_name ? (
                <span>
                  {props.counselor_first_name} {props.counselor_last_name}
                </span>
              ) : (
                <span className="text-gray-400">No counselor assigned</span>
              )}
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  );
}

export default CamperCareBunkLogItem;
