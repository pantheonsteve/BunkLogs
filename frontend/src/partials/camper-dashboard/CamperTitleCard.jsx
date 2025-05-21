
import React, { useState, useEffect } from 'react';
import axios from 'axios';



function CamperTitleCard({ camper_id }){

    const [data, setData] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
          try {
            // Format the date as "YYYY-MM-DD" if needed.
            //const formattedDate = date.toISOString().split('T')[0];
            // Build the URL dynamically using bunk and formattedDate.
            const response = await axios.get(
              `https://dev-camper-care-bunk-logs.pantheonsite.io/api/v1/camper/info/${camper_id}`
            );
            setData(response.data);
          } catch (error) {
            // Use the 'error' variable consistently.
            if (axios.isAxiosError(error) && error.response) {
              if (error.response.status === 404) {
                setError(
                  error.response.data.message ||
                    `Missing camper ID for ${camper_id}`
                );
              } else {
                setError("An error occurred while fetching the summary.");
              }
            } else {
              console.error("Error:", error);
              setError('An unexpected error occurred.');
            }
          } finally {
            setLoading(false);
          }
        };
    
        fetchData();
      });

      if (loading) return <p>Loading...</p>;
      if (error) return <p>Error: {error}</p>;

      return (
        <div className="col-span-full xl:col-span-4 shadow-xs rounded-xl">
            
            {data.map((item) => (
                <h1>{item.first_name} {item.last_name}</h1>
              ))}
        </div>

      );
}

export default CamperTitleCard;