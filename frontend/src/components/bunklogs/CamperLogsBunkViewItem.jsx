import React, { useState } from 'react';
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
  };

  const [open, setOpen] = useState(false);

  return (
    <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
      <tr>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
        <Link className="font-medium text-gray-800 dark:text-gray-100" to={`/camper/${props.camper_id}/${props.date}`}>
          <div className="flex items-center text-gray-800">
            <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-2 sm:mr-3">
              <img className="rounded-full ml-1" src={props.image ? props.image : GenericAvatar} width="40" height="40" alt={props.customer} />
            </div>
            <div className="font-medium text-gray-800 dark:text-gray-100">{props.camper_first_name} {props.camper_last_name}</div>
          </div>
        </Link>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{props.date}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(props.social_score)}`}>
          <div className="text-center">{props.social_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(props.behavior_score)}`}>
          <div className="text-center">{props.behavior_score}</div>
        </td>
        <td className={`px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap ${getScoreBackgroundColor(props.participation_score)}`}>
          <div className="text-center">{props.participation_score}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{getHelpRequestedIcon(props.camper_care_help)}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{getHelpRequestedIcon(props.unit_head_help)}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap w-px">
          <div className="flex items-center">
            <button
              className={`text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400 ${open && 'rotate-180'}`}
              aria-expanded={open}
              onClick={() => setOpen(!open)}
              aria-controls={`description-${props.id}`}
            >
              <span className="sr-only">Menu</span>
              <svg className="w-8 h-8 fill-current" viewBox="0 0 32 32">
                <path d="M16 20l-5.4-5.4 1.4-1.4 4 4 4-4 1.4 1.4z" />
              </svg>
            </button>
          </div>
        </td>
      </tr>
      {/*
      Example of content revealing when clicking the button on the right side:
      Note that you must set a "colSpan" attribute on the <td> element,
      and it should match the number of columns in your table
      */}
      <tr id={`description-${props.id}`} role="region" className={`${!open && 'hidden'}`}>
        <td colSpan="10" className="px-2 first:pl-5 last:pr-5 py-3">
          <div className="bg-gray-50 dark:bg-gray-950/[0.15] dark:text-gray-400 p-3 -mt-3">
            <div className="text-sm mb-3">
              {/* Note: Using dangerouslySetInnerHTML requires that content is properly sanitized to prevent XSS attacks */}
              <div dangerouslySetInnerHTML={{ __html: props.description }}></div>
              <div className="font-medium text-blue-500 dark:text-gray-100 mb-1 text-right">Reporting Counselor: {props.counselor_first_name} {props.counselor_last_name}</div>
            </div>
          </div>
        </td>
      </tr>
    </tbody>
  );
}

export default CamperLogsBunkViewItem;