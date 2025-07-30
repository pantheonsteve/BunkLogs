import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import CamperLogsBunkViewItem from '../../components/bunklogs/CamperLogsBunkViewItem';

import Image01 from '../../images/user-36-05.jpg';
import Image02 from '../../images/user-36-06.jpg';
import Image03 from '../../images/user-36-07.jpg';
import Image04 from '../../images/user-36-08.jpg';
import Image05 from '../../images/user-36-09.jpg';
import axios from 'axios';

function BunkLogsTableViewCard({ bunkData }) {

  // Sample data for the table
  const items = [
    {
      id: '0',
      image: Image01,
      camper_first_name: 'Mark',
      camper_last_name: 'Cameron',
      email: 'mark.cameron@app.com',
      counselor_name: 'John Doe',
      date: '2023-10-01',
      social_score: '5',
      behavior_score: '4',
      participation_score: '3',
      camper_care_help: 'true',
      unit_head_help: 'false',
      descriptionTitle: 'Excepteur sint occaecat cupidatat.',
      descriptionBody: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam quis. Ut enim ad minim veniam quis. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
    },
  ];

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);  // Changed to false since data is passed as prop
  const [data, setData] = useState([]);
  

  const filterNotOnCamp = (campers) => {
    if (!Array.isArray(campers)) return [];
    return campers.filter((camper) => camper.bunk_log?.not_on_camp === false);
  }

  useEffect(() => {
    if (bunkData && bunkData.campers) {
      setData(filterNotOnCamp(bunkData.campers));
    } else {
      setData([]);
    }
  }, [bunkData]);

  // Get the Counselor Name from the ID
  const getCounselorName = (counselorId, data) => {
    // First check in bunk.counselors (primary location in your data)
    const counselor = data?.bunk?.counselors?.find((c) => c.id === counselorId);
    
    // If found, return the name
    if (counselor) {
      return `${counselor.first_name} ${counselor.last_name}`;
    }
    return "Unknown";
  }

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

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div className="col-span-full bg-white dark:bg-gray-800 shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
      <div className="p-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">Camper Logs</h2>
        
        {/* Table Container with horizontal scroll for mobile */}
        <div className="overflow-x-auto">
          <div className="rounded-lg border border-gray-200 dark:border-gray-700/60">
            <div className="overflow-x-auto w-full">
              <table className="table-auto w-full dark:text-gray-300">
                {/* Table header */}
                <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
                  <tr>
                    {/* Column width: 2/12 */}
                    <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                      <div className="font-semibold text-left">Camper Name</div>
                    </th>
                    {/* Column width: 1/12 */}
                    <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700">
                      <div className="font-semibold text-center">Date</div>
                    </th>
                    {/* Column width: 2/12 */}
                    <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                      <div className="font-semibold text-center">Social</div>
                    </th>
                    {/* Column width: 2/12 */}
                    <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                      <div className="font-semibold text-center">Behavior</div>
                    </th>
                    {/* Column width: 2/12 */}
                    <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                      <div className="font-semibold text-center">Participation</div>
                    </th>
                    {/* Description column - wider now */}
                    <th className="p-2 border-b border-gray-200 dark:border-gray-700" style={{ minWidth: '400px' }}>
                      <div className="font-semibold text-left">Description</div>
                    </th>
                  </tr>
                </thead>
                {Array.isArray(data) && data.length > 0 ? (
                  data.map((item, index) => {
                    const uniqueKey = item.id || `${item.camper_first_name}-${item.camper_last_name}-${index}`;
                    const counselor = item?.bunk_assignment?.bunk?.counselors?.find(c => c.id === item.bunk_log.counselor) || "Unknown";
                    const counselorName = `${counselor.first_name} ${counselor.last_name}`;
                    console.log("Counselor Name: ", getCounselorName(item.bunk_log.counselor, item));
                    console.log("data: ", data);
                    console.log("item: ", item);
                    console.log("item.bunk_log: ", item.bunk_log);
                    console.log("item.bunk_log.counselor: ", item.bunk_log.counselor);
                    return (
                      <CamperLogsBunkViewItem
                        key={uniqueKey}
                        id={item.id}
                        camper_id={item.camper_id}
                        image={item.image}
                        camper_first_name={item.camper_first_name}
                        camper_last_name={item.camper_last_name}
                        counselor_first_name={item.bunk_log.counselor_first_name}
                        counselor_last_name={item.bunk_log.counselor_last_name}
                        counselor_email={item.bunk_log.counselor_email}
                        social_score={item.bunk_log.social_score}
                        behavior_score={item.bunk_log.behavior_score}
                        participation_score={item.bunk_log.participation_score}
                        camper_care_help={item.bunk_log.request_camper_care_help}
                        unit_head_help={item.bunk_log.request_unit_head_help}
                        date={item.bunk_log.date}
                        description={item.bunk_log.description}
                      />
                    )
                  })
                ) : (
                  <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
                    <tr>
                      <td colSpan="6" className="p-4 text-center text-gray-500 dark:text-gray-400">
                        {loading ? 'Loading camper logs...' : 'No camper logs found'}
                      </td>
                    </tr>
                  </tbody>
                )}
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BunkLogsTableViewCard;