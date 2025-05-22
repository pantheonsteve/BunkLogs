import React, { useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chart.js/auto';
import { addDays, subDays, format } from 'date-fns';

const CamperScoresChart = ({ logEntries = [] }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  console.log('CamperScoresChart logEntries:', logEntries); // Debug

  useEffect(() => {
    if (!chartRef.current) return;

    // Clean up previous chart
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');

    // Create gradients for each score type
    const socialGradient = ctx.createLinearGradient(0, 0, 0, 400);
    socialGradient.addColorStop(0, '#14d127');    // 5 (top)
    socialGradient.addColorStop(0.25, '#8fd258'); // 4
    socialGradient.addColorStop(0.5, '#e5e824');  // 3
    socialGradient.addColorStop(0.75, '#de8d6f'); // 2
    socialGradient.addColorStop(1, '#e76846');    // 1 (bottom)

    const behaviorGradient = ctx.createLinearGradient(0, 0, 0, 400);
    behaviorGradient.addColorStop(0, '#14d127');
    behaviorGradient.addColorStop(0.25, '#8fd258');
    behaviorGradient.addColorStop(0.5, '#e5e824');
    behaviorGradient.addColorStop(0.75, '#de8d6f');
    behaviorGradient.addColorStop(1, '#e76846');

    const participationGradient = ctx.createLinearGradient(0, 0, 0, 400);
    participationGradient.addColorStop(0, '#14d127');
    participationGradient.addColorStop(0.25, '#8fd258');
    participationGradient.addColorStop(0.5, '#e5e824');
    participationGradient.addColorStop(0.75, '#de8d6f');
    participationGradient.addColorStop(1, '#e76846');

    // Generate 60-day timeline (from 59 days ago to today)
    const today = new Date();
    const startDate = subDays(today, 59);
    
    // Create array of all dates in the 60-day period
    const allDates = Array.from({ length: 60 }, (_, i) => {
      const date = addDays(startDate, i);
      return {
        date: date,
        formattedDate: format(date, 'MMM d'),
        timestamp: date.getTime()
      };
    });

    // Map the log entries to their corresponding dates
    const filteredEntries = logEntries
      .filter(entry => entry.date && !entry.not_on_camp);
      
    // Create lookup map for quick access to entry data by date
    const entriesByDate = {};
    filteredEntries.forEach(entry => {
      const entryDate = new Date(entry.date);
      const dateKey = format(entryDate, 'yyyy-MM-dd');
      entriesByDate[dateKey] = {
        social: entry.social_score,
        behavior: entry.behavior_score,
        participation: entry.participation_score
      };
    });

    // Map scores to the timeline - use null for dates without data
    const timelineData = allDates.map(dateObj => {
      const dateKey = format(dateObj.date, 'yyyy-MM-dd');
      const entry = entriesByDate[dateKey] || { social: null, behavior: null, participation: null };
      
      return {
        x: dateObj.date,
        social: entry.social,
        behavior: entry.behavior,
        participation: entry.participation
      };
    });

    // Prepare datasets with x-y coordinate format for time scale
    const datasets = [];
    
    // Check if we have social data
    const hasSocialData = timelineData.some(item => item.social !== null);
    if (hasSocialData) {
      datasets.push({
        label: 'Social Score',
        data: timelineData.map(item => ({
          x: item.x,
          y: item.social
        })),
        backgroundColor: 'transparent',
        borderColor: socialGradient,
        borderWidth: 3,
        fill: false,
        tension: 0,
        pointBackgroundColor: '#2563eb',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: (ctx) => ctx.parsed.y === null ? 0 : 5,
        pointHoverRadius: 7,
        spanGaps: true
      });
    }

    // Check if we have behavior data
    const hasBehaviorData = timelineData.some(item => item.behavior !== null);
    if (hasBehaviorData) {
      datasets.push({
        label: 'Behavior Score',
        data: timelineData.map(item => ({
          x: item.x,
          y: item.behavior
        })),
        backgroundColor: 'transparent',
        borderColor: behaviorGradient,
        borderWidth: 3,
        fill: false,
        tension: 0,
        pointBackgroundColor: '#dc2626',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: (ctx) => ctx.parsed.y === null ? 0 : 5,
        pointHoverRadius: 7,
        spanGaps: true
      });
    }

    // Check if we have participation data
    const hasParticipationData = timelineData.some(item => item.participation !== null);
    if (hasParticipationData) {
      datasets.push({
        label: 'Participation Score',
        data: timelineData.map(item => ({
          x: item.x,
          y: item.participation
        })),
        backgroundColor: 'transparent',
        borderColor: participationGradient,
        borderWidth: 3,
        fill: false,
        tension: 0,
        pointBackgroundColor: '#059669',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: (ctx) => ctx.parsed.y === null ? 0 : 5,
        pointHoverRadius: 7,
        spanGaps: true
      });
    }

    // Register Chart.js components
    ChartJS.register(
      CategoryScale,
      LinearScale,
      PointElement,
      LineElement,
      Title,
      Tooltip,
      Legend,
      TimeScale
    );

    chartInstance.current = new ChartJS(ctx, {
      type: 'line',
      data: {
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 20,
              font: {
                size: 12,
                weight: '500'
              }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#333',
            borderWidth: 1,
            titleFont: {
              size: 14,
              weight: 'bold'
            },
            bodyFont: {
              size: 12
            },
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              title: function(tooltipItems) {
                if (!tooltipItems.length) return '';
                const date = new Date(tooltipItems[0].parsed.x);
                return format(date, 'MMM d, yyyy');
              }
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day',
              displayFormats: {
                day: 'MMM d'
              }
            },
            display: true,
            title: {
              display: true,
              text: 'Date',
              font: {
                size: 14,
                weight: 'bold'
              },
              color: '#374151'
            },
            ticks: {
              color: '#6b7280',
              font: {
                size: 11
              },
              maxRotation: 45,
              minRotation: 45
            },
            grid: {
              color: 'rgba(0,0,0,0.1)',
              lineWidth: 1
            },
            min: startDate,
            max: today
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Score',
              font: {
                size: 14,
                weight: 'bold'
              },
              color: '#374151'
            },
            min: 0,
            max: 6,
            ticks: {
              stepSize: 1,
              color: '#6b7280',
              font: {
                size: 11
              },
              callback: function(value) {
                return Math.floor(value);
              }
            },
            grid: {
              color: 'rgba(0,0,0,0.1)',
              lineWidth: 1
            }
          }
        }
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [logEntries]);

  const camperName = logEntries.length > 0 
    ? `${logEntries[0].camper.first_name} ${logEntries[0].camper.last_name}`
    : 'Camper';

  return (
    <div className="flex flex-col col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl"> 
      <div className="relative h-96">
        <canvas ref={chartRef}></canvas>
      </div>
      
      {logEntries.length === 0 && (
        <div className="text-center text-gray-500 mt-4">
          No log entries available to display
        </div>
      )}
    </div>
  );
};

export default CamperScoresChart;