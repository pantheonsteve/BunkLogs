import React, { useState, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import axios from 'axios';


function CamperList({ bunk_id, date, openBunkModal, refreshTrigger }) {

    const [data, setData] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
          try {
            setLoading(true);
            const response = await axios.get(
              //`https://dev-camper-care-bunk-logs.pantheonsite.io/api/v1/campers?bunk_id=${bunk_id}`
              `http://localhost:8000/api/v1/bunklogs/${bunk_id}/logs/${date}/`
            );
            setData(response.data.campers);
          } catch (error) {
            setError('Error fetching campers.');
          } finally {
            setLoading(false);
          }
        };
        fetchData();
    }, [bunk_id, date, refreshTrigger]); // Added refreshTrigger as a dependency

    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error: {error}</p>;

    return (
      <div>
          {data.map((camper) => (
                  <p key={camper.camper_id} className='w-full'>
                      <button
                        className={`btn text-black-100 ${camper.bunk_log ? 'has-bunklog' : ''}`}
                        aria-controls="feedback-modal"
                        onClick={(e) => {
                          console.log('Clicked');
                          console.log(camper);
                          e.stopPropagation();
                          // Use the function from props and pass camper_id
                          openBunkModal(camper.camper_id, camper.bunk_assignment_id);
                        }}
                        title={camper.bunk_log ? "View/Edit Bunk Log" : "Create Bunk Log"}
                      >
                        <span>
                          {camper.bunk_log ? (
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="green" className="size-5">
                              <path fillRule="evenodd" d="M8.603 3.799A4.49 4.49 0 0 1 12 2.25c1.357 0 2.573.6 3.397 1.549a4.49 4.49 0 0 1 3.498 1.307 4.491 4.491 0 0 1 1.307 3.497A4.49 4.49 0 0 1 21.75 12a4.49 4.49 0 0 1-1.549 3.397 4.491 4.491 0 0 1-1.307 3.497 4.491 4.491 0 0 1-3.497 1.307A4.49 4.49 0 0 1 12 21.75a4.49 4.49 0 0 1-3.397-1.549 4.49 4.49 0 0 1-3.498-1.306 4.491 4.491 0 0 1-1.307-3.498A4.49 4.49 0 0 1 2.25 12c0-1.357.6-2.573 1.549-3.397a4.49 4.49 0 0 1 1.307-3.497 4.49 4.49 0 0 1 3.497-1.307Zm7.007 6.387a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z" clipRule="evenodd" />
                            </svg>                          
                          ) : (
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="red" className="size-5">
                            <path fillRule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25Zm-1.72 6.97a.75.75 0 1 0-1.06 1.06L10.94 12l-1.72 1.72a.75.75 0 1 0 1.06 1.06L12 13.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L13.06 12l1.72-1.72a.75.75 0 1 0-1.06-1.06L12 10.94l-1.72-1.72Z" clipRule="evenodd" />
                          </svg>
                          )}
                          </span>
                          <span className="text-sm font-medium lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">    
                           {camper.camper_first_name} {camper.camper_last_name}
                        </span>
                      </button>
                    </p>
                  ) 
                )
              }
          </div>
    );
}

export default CamperList;