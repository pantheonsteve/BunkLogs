import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function CamperLogsCamperViewItem(props) {

  const getBunkIdForBunkLog = (bunk_log) => {
      // Check if bunk_log is an object and has the 'bunk' property
      // console.log('IN FUNCTION', bunk_log);
      if ((typeof bunk_log === 'object') && (bunk_log !== null) && ('bunk_assignment' in bunk_log)) {
          // Check if 'bunk' is an object and has the 'id' property
          if ((typeof bunk_log.bunk_assignment === 'object') && (bunk_log.bunk_assignment !== null) && ('id' in bunk_log.bunk_assignment)) {
              const bunk_assignment = bunk_log.bunk_assignment;
              if (bunk_assignment && bunk_assignment.bunk_id) {
                  return bunk_assignment.bunk_id;
              }
          }}
      // Return null if the bunk ID is not found
      return null;
  }

  //console.log('Bunk ID:', getBunkIdForBunkLog(props)); // Debug

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

  //console.log(props); // Debug

  const [open, setOpen] = useState(false);

  // console.log('CamperLogsCamperViewItem props:', props); // Debug

  return (
    <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-700/60">
      <tr>
        <td className="p-3 whitespace-wrap">
        <Link 
          className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap" 
          to={`/bunk/${props.bunk_id}/${props.date}`}
          state={{ selectedDate: props.date }}
        >
          
            <div className="text-center">{props.date}</div>
          
        </Link>
        </td>
        { props.not_on_camp === false && (
        <>
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
            <div className="text-center">{getHelpRequestedIcon(props.request_camper_care_help)}</div>
          </td>
          <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
            <div className="text-center">{getHelpRequestedIcon(props.request_unit_head_help)}</div>
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
        </>
        )}
        {props.not_on_camp === true && (
          <td className="px-12 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
            <div className="text-center">
              <h2>Not On Camp</h2>
            </div>
          </td>
        )}
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

export default CamperLogsCamperViewItem;