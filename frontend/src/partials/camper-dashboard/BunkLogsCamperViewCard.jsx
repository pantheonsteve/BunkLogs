import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import CamperLogsCamperViewItem from '../../components/bunklogs/CamperLogsCamperViewItem';


import Image01 from '../../images/user-36-05.jpg';
import Image02 from '../../images/user-36-06.jpg';
import Image03 from '../../images/user-36-07.jpg';
import Image04 from '../../images/user-36-08.jpg';
import Image05 from '../../images/user-36-09.jpg';

function BunkLogsCamperViewCard({camperData}) {

    // Define state for the fetched data, error and loading status.
      const [error, setError] = useState(null);
      const [loading, setLoading] = useState(false);  // Changed to false since data is passed as prop
      const [data, setData] = useState([]);

      if (loading) return <p>Loading...</p>;
      if (error) return <p>Error: {error}</p>;

      console.log('Rendering BunkLogsCamperViewCard:', camperData); // Debug

      const filterNoNotes = (data) => {
        return camperData.filter((item) => item?.description !== '');
      }

      const bunk_logs = camperData.bunk_logs;
    //   console.log('Bunk Logs:', bunk_logs); // Works
    //   console.log('Camper Data:', camperData); // Debug
      

      useEffect(() => {
        setData(data.filter((item) => item?.description !== false));
      }, [camperData]);

      if (loading) return <p>Loading...</p>;
      if (error) return <p>Error: {error.message}</p>;

    //   console.log('Rendering BunkLogsCamperViewCard:', data); // Debug
    //   console.log('Bunk Assignments:', camperData.bunk_assignments); // Debug
      
      const getBunkIdFromBunkAssignment = (bunk_assignment) => {
        if (camperData.bunk_assignments && camperData.bunk_assignments.length > 0) {
            const bunkAssignment = camperData.bunk_assignments.find(assignment => assignment.id === bunk_assignment);
            if (bunkAssignment) {
                return bunkAssignment.bunk_id;
            }
        }
      } // Debug

        // console.log('Bunk ID:', getBunkIdFromBunkAssignment('9')); // Debug

      return (

        <div className="col-span-full xl:col-span-12 bg-white dark:bg-gray-800 shadow-xs rounded-xl">
            <div className="p-3">

                {/* Table */}
                <div className="overflow-x-auto">
                <table>
                <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
                        <tr>
                            {/* Column width: 2/12 */}
                            <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-left">Date</div>
                            </th>
                            <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-left">Social Score</div>
                            </th>
                            <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-left">Behavior Score</div>
                            </th>
                            <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-left">Participation Score</div>
                            </th>
                            <th className="p-2 border-b border-gray-200 dark:border-gray-700" style={{ minWidth: '400px' }}>
                                <div className="font-semibold text-left">Description</div>
                            </th>
                        </tr>
                    </thead>
                        {bunk_logs?.map((item) => (
                            <CamperLogsCamperViewItem 
                                key={item.id}
                                id={item.id}
                                bunk_assignment_id={item.bunk_assignment.id}
                                bunk_id={item.bunk_assignment.bunk.id}
                                date={item.date}
                                not_on_camp={item.not_on_camp}
                                social_score={item.social_score}
                                behavior_score={item.behavior_score}
                                participation_score={item.participation_score}
                                request_camper_care_help={item.request_camper_care_help}
                                request_unit_head_help={item.request_unit_head_help}
                                description={item.description}
                                counselor_first_name={item.counselor.first_name}
                                counselor_last_name={item.counselor.last_name}
                            />
                        ))}
                </table>
            </div>
        </div>
    </div>
      );
}

export default BunkLogsCamperViewCard;
