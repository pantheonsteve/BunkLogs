import React, { useState, useEffect, useRef } from 'react';
import { chartAreaGradient } from '../../charts/ChartjsConfig';
import LineChart from '../../charts/LineChart02';
import { getCssVariable } from '../../utils/Utils';

function ScoresLineChartCard({ camperData }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const legendRef = useRef(null);

  // Score-based colors for points and labels
  const scoreColors = {
    1: '#E76846', // Red
    2: '#DE8D6F', // Orange
    3: '#E5E824', // Yellow
    4: '#8FD258', // Green
    5: '#14D127'  // Dark Green
  };

  // Grayscale colors for lines
  const metrics = {
    social: {
      label: 'Social',
      color: '#4B5563'  // Dark gray
    },
    behavior: {
      label: 'Behavior',
      color: '#6B7280'  // Medium gray
    },
    participation: {
      label: 'Participation',
      color: '#9CA3AF'  // Light gray
   /* */}
  };

  const formatDate = (dateStr) => {
    const [year, month, day] = dateStr.split('-');
    return `${month}-${day}-${year}`;
  };

  useEffect(() => {
    if (!camperData || !Array.isArray(camperData) || camperData.length === 0) {
      setChartData(null);
      return;
    }

    try {
      // Calculate date 60 days ago
      const sixtyDaysAgo = new Date();
      sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60);
      
      const processedData = [...camperData]
        // Filter data to only include entries from the past 60 days
        .filter(entry => new Date(entry.date) >= sixtyDaysAgo)
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .map(entry => ({
          date: formatDate(entry.date),
          social: parseInt(entry.social_score),
          behavior: parseInt(entry.behavior_score),
          participation: parseInt(entry.participation_score)
        }));
 
      console.log('Processed Data:', processedData); // Debug

      const createDataset = (key, label, color) => ({
        label,
        data: processedData.map(entry => entry[key]),
        borderColor: color,
        fill: false,
        borderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8,
        pointBackgroundColor: (context) => {
          const value = context.raw;
          return scoreColors[value] || '#666666';
        },
        pointHoverBackgroundColor: (context) => {
          const value = context.raw;
          return scoreColors[value] || '#666666';
        },
        pointBorderColor: (context) => {
          const value = context.raw;
          return scoreColors[value] || '#666666';
        },
        pointBorderWidth: 2,
        pointHoverBorderWidth: 2,
        clip: 20,
        tension: 0.0,
        spanGaps: true
      });

      setChartData({
        labels: processedData.map(entry => entry.date),
        datasets: Object.entries(metrics).map(([key, {label, color}]) => 
          createDataset(key, label, color)
        )
      });
    } catch (err) {
      setError(err.message);
      console.error('Error processing chart data:', err);
    }
  }, [camperData]);

  const chartOptions = {
    formatYAxisLabel: (value) => {
      if (value >= 1 && value <= 5) {
        return value.toString();
      }
      return '';
    },
    yAxis: {
      min: 1,
      max: 5,
      grid: {
        color: (context) => {
          const value = Math.floor(context.tick.value);
          if (value >= 1 && value <= 5) {
            return scoreColors[value] + '30'; // More transparent
          }
          return '#E5E7EB';
        },
        z: -1
      },
      ticks: {
        stepSize: 1,
        font: {
          weight: 700,  // Bolder
          size: 14      // Slightly larger
        },
        color: (context) => {
          const value = context.tick.value;
          if (value >= 1 && value <= 5) {
            return scoreColors[value];
          }
          return '#666666';
        }
      }
    },
    tooltip: {
      intersect: true,
      mode: 'nearest',
      callbacks: {
        title: function(tooltipItems) {
          if (!tooltipItems.length) return '';
          // Format the date more clearly
          const dateParts = tooltipItems[0].label.split('-');
          if (dateParts.length === 3) {
            const [month, day, year] = dateParts;
            const date = new Date(`${year}-${month}-${day}`);
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'long', day: 'numeric' });
          }
          return tooltipItems[0].label;
        },
        label: function(context) {
          return `${context.dataset.label}: ${context.raw}`;
        }
      }
    }
  };

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  if (!chartData) return <p>No data available</p>;

  return (
    <div className="flex flex-col col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">Camper Scores</h2>
      </header>
      <div className="px-5 py-1">
        <div className="flex flex-wrap justify-end items-center">
          <div className="grow">
            <div className="flex flex-wrap gap-2 justify-end">
              {Object.entries(metrics).map(([key, {label, color}]) => (
                <div key={key} className="flex items-center">
                  <span 
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="w-full h-72">
        <LineChart 
          data={chartData} 
          options={chartOptions} 
          width={595} 
          height={248} 
        />
      </div>
    </div>
  );
}

export default ScoresLineChartCard;