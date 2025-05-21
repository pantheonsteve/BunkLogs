import React from 'react';
import { NavLink } from 'react-router-dom';
import { useBunk } from '../../contexts/BunkContext';

function CamperPageCamperList({ bunk_id, date }) {
    // Get data from context instead of making a separate API call
    const { bunkData, loading, error } = useBunk();
    
    // Use the campers data from the context
    const campers = bunkData?.campers || [];
    
    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error: {error?.message || 'Error fetching campers'}</p>;

    console.log('CamperList data:', bunkData); // Debug

    return (
      <div>
          {campers.map((camper) => (
                  <p key={camper.camper_id} className='w-full'>
                    <NavLink
                      className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap"
                      to={`/camper/${camper.camper_id}`}
                    >
                      <td className="p-3 whitespace-wrap">
                        <div className="text-center">{camper.camper_first_name} {camper.camper_last_name}</div>
                      </td>
                    </NavLink>
                    </p>
                  ) 
                )
              }
          </div>
    );
}

export default CamperPageCamperList;