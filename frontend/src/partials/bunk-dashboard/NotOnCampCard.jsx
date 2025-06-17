import React, { useState, useEffect } from 'react';
import { useBunk } from '../../contexts/BunkContext';

import GenericAvatar from '../../images/avatar-generic.png';

function NotOnCampCard({ bunkData }) {

  const { bunkBunkData } = useBunk();


  const date = bunkData.date;
  const campers = bunkData.campers;

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);  // Changed to false since data is passed as prop
  const [data, setData] = useState(bunkData);

  const filterNotOnCamp = (campers) => {
    return campers.filter((camper) => camper.bunk_log?.not_on_camp == true);
  }

  useEffect(() => {
    if (bunkData && bunkData.campers) {
      setData(filterNotOnCamp(bunkData.campers));
    }
  }, [bunkData]);

  return (
    <div className="col-span-full xl:col-span-4 bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">Not On Camp</h2>
      </header>
      <div className="p-3">
        {/* Table */}
        <div className="overflow-x-auto">
          <table className="table-auto w-full dark:text-gray-300">
            {/* Table header */}
            <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
              <tr>
                <th className="p-2">
                  <div className="font-semibold text-left">Camper Name</div>
                </th>
                <th className="p-2">
                  <div className="font-semibold text-center">Bunk</div>
                </th>
              </tr>
            </thead>
            {/* Table body */}
            <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
              {/* Row */}
              {Array.isArray(data) ? (
                data.map((item, index) => {
                  // Create a reliable key using camper info or fallback to index
                  const uniqueKey = item.id || `${item.camper_first_name}-${item.camper_last_name}-${index}`;
                  return (
                    <tr key={uniqueKey}>
                      <td className="p-2">
                        <div className="flex items-center">
                          <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-2 sm:mr-3">
                            <img className="rounded-full ml-1" width="36" height="36" viewBox="0 0 36 36" src={GenericAvatar} />
                          </div>
                          <div className="text-gray-800 dark:text-gray-100">{item.camper_first_name} {item.camper_last_name}</div>
                        </div>
                      </td>
                      <td className="p-2">
                        <div className="text-center">{item.bunk_label}</div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan="2" className="p-2 text-center">No data available</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>

  );
}

export default NotOnCampCard;