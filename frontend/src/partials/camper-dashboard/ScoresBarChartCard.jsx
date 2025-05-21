import React from 'react';
import BarChart from '../../charts/BarChart01';

// Import utilities
import { getCssVariable } from '../../utils/Utils';

function ScoresBarChartCard({ camperData }) {
    // Properly destructured props to get camperData
    
    console.log('ScoresBarChart Data', camperData);
    console.log(typeof camperData, camperData);
    
    let dateLabels = [];
    let socialScores = [];
    let behaviorScores = [];
    let participationScores = [];
    
    // Handle different data formats
    if (camperData) {
        if (Array.isArray(camperData)) {
            // If camperData is already an array
            dateLabels = camperData.map(data => data.date);
            socialScores = camperData.map(data => data.social_score);
            behaviorScores = camperData.map(data => data.behavior_score);
            participationScores = camperData.map(data => data.participation_score);
        } else {
            // If camperData is an object
            // Option 1: Convert object to array if it has numeric keys
            if (Object.keys(camperData).every(key => !isNaN(key))) {
                dateLabels = Object.values(camperData).map(data => data.date);
                socialScores = Object.values(camperData).map(data => data.social_score);
                behaviorScores = Object.values(camperData).map(data => data.behavior_score);
                participationScores = Object.values(camperData).map(data => data.participation_score);
            } 
            // Option 2: If object has specific structure with dates property
            else if (camperData.dates) {
                dateLabels = camperData.dates;
            }
            // Option 3: Extract keys if they represent dates
            else if (Object.keys(camperData).length > 0) {
                dateLabels = Object.keys(camperData);
            }
        }
    }

    console.log('behaviorScores', behaviorScores);
    console.log('socialScores', socialScores);
    console.log('participationScores', participationScores);
    
    console.log('dateLabels', dateLabels);

  const chartData = {
    labels: dateLabels,
    datasets: [
      // Light blue bars
      {
        label: 'Social',
        data: socialScores,
        backgroundColor: getCssVariable('--color-sky-500'),
        hoverBackgroundColor: getCssVariable('--color-sky-600'),
        barPercentage: 0.7,
        categoryPercentage: 0.7,
        borderRadius: 4,
      },
      // Blue bars
      {
        label: 'Behavior',
        data: behaviorScores,
        backgroundColor: getCssVariable('--color-violet-500'),
        hoverBackgroundColor: getCssVariable('--color-violet-600'),
        barPercentage: 0.7,
        categoryPercentage: 0.7,
        borderRadius: 4,
      },
      // Red bars
      {
        label: 'Participation',
        data: participationScores,
        backgroundColor: getCssVariable('--color-red-500'),
        hoverBackgroundColor: getCssVariable('--color-red-600'),
        barPercentage: 0.7,
        categoryPercentage: 0.7,
        borderRadius: 4,
      },
    ],
  };

  return (
    <div className="flex flex-col col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">Direct VS Indirect</h2>
      </header>
      {/* Chart built with Chart.js 3 */}
      {/* Change the height attribute to adjust the chart height */}
      <BarChart data={chartData} width={595} height={248} />
    </div>
  );
}

export default ScoresBarChartCard;
