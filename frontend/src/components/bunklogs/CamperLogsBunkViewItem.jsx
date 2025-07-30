import React from 'react';
import { Link } from 'react-router-dom';
import { useBunk } from '../../contexts/BunkContext';
import GenericAvatar from '../../images/avatar-generic.png';

function CamperLogsBunkViewItem(props) {

  const { bunkDigityData, loading, error } = useBunk();

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

  return (
    <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
      <tr>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
        <Link className="font-medium text-gray-800 dark:text-gray-100" to={`/camper/${props.camper_id}/${props.date}`}>
          <div className="flex items-center text-gray-800">
            <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-2 sm:mr-3">
              <img className="rounded-full ml-1" src={props.image ? props.image : GenericAvatar} width="40" height="40" alt={props.customer} />
            </div>
            <div>
              <div className="font-medium text-gray-800 dark:text-gray-100">{props.camper_first_name} {props.camper_last_name}</div>
              {/* Help request indicators below camper name */}
              <div className="flex flex-wrap gap-1 mt-1">
                {props.camper_care_help && (
                  <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded text-red-700 bg-red-100 border border-red-200">
                    <svg className="w-3 h-3 mr-1 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path d="M18 13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v6zm-1-6H3v6h14V7zm-7 2a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1z"/></svg>
                    CC Help
                  </span>
                )}
                {props.unit_head_help && (
                  <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded text-yellow-800 bg-yellow-100 border border-yellow-200">
                    <svg className="w-3 h-3 mr-1 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm1 12H9v-2h2v2zm0-4H9V6h2v4z"/></svg>
                    UH Help
                  </span>
                )}
              </div>
            </div>
          </div>
        </Link>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
          <div className="text-center">{props.date}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.social_score)}`}>
          <div className="text-center">{props.social_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.behavior_score)}`}>
          <div className="text-center">{props.behavior_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 ${getScoreBackgroundColor(props.participation_score)}`}>
          <div className="text-center">{props.participation_score}</div>
        </td>
        {/* Description column - always visible and wider */}
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-pre-line break-words align-top border border-gray-300 dark:border-gray-700" style={{ maxWidth: '400px' }}>
          <div className="text-gray-700 dark:text-gray-200 text-sm" style={{ whiteSpace: 'pre-line' }}>
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
                  {props.counselor_email && (
                    <span className="block text-xs text-gray-400">{props.counselor_email}</span>
                  )}
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

export default CamperLogsBunkViewItem;