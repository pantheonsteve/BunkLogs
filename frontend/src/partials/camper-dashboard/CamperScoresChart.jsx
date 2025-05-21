import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const CamperScoresChart = () => {
  // Sample data based on your API response
  const rawData = [
    {date: '2025-04-13', counselor: 3, social_score: null, behavior_score: null, participation_score: null},
    {date: '2025-04-12', counselor: 1, social_score: 2, behavior_score: 1, participation_score: 4},
    {date: '2025-04-11', counselor: 3, social_score: 3, behavior_score: 3, participation_score: 3},
    {date: '2025-04-10', counselor: 1, social_score: 4, behavior_score: 4, participation_score: 5},
    {date: '2025-04-09', counselor: 3, social_score: 3, behavior_score: 3, participation_score: 3},
    {date: '2025-04-08', counselor: 3, social_score: 3, behavior_score: 3, participation_score: 3},
    {date: '2025-04-07', counselor: 3, social_score: 3, behavior_score: 3, participation_score: 3},
    {date: '2025-04-05', counselor: 3, social_score: null, behavior_score: null, participation_score: null},
    {date: '2025-03-31', counselor: 1, social_score: 5, behavior_score: 1, participation_score: 3},
    {date: '2025-03-30', counselor: 1, social_score: null, behavior_score: null, participation_score: null},
    {date: '2025-03-29', counselor: 1, social_score: 5, behavior_score: 2, participation_score: 3},
    {date: '2025-03-28', counselor: 1, social_score: 4, behavior_score: 3, participation_score: 3},
    {date: '2025-03-27', counselor: 1, social_score: 3, behavior_score: 4, participation_score: 4},
    {date: '2025-02-24', counselor: 3, social_score: 3, behavior_score: 5, participation_score: 4}
  ];

  // Filter out entries with null scores
  const [chartData, setChartData] = useState([]);
  const [viewMode, setViewMode] = useState('all'); // 'all', 'recent', 'month'
  
  useEffect(() => {
    // Format dates and filter out null scores
    const processedData = rawData
      .filter(item => item.social_score !== null || item.behavior_score !== null || item.participation_score !== null)
      .map(item => {
        // Format the date for display
        const date = new Date(item.date);
        const formattedDate = `${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
        
        return {
          date: item.date,
          displayDate: formattedDate,
          social_score: item.social_score,
          behavior_score: item.behavior_score,
          participation_score: item.participation_score,
          counselor: item.counselor
        };
      })
      .sort((a, b) => new Date(a.date) - new Date(b.date)); // Sort by date ascending
    
    setChartData(processedData);
  }, []);

  // Filter data based on view mode
  const getFilteredData = () => {
    if (viewMode === 'recent') {
      // Show last 7 days with data
      return chartData.slice(-7);
    } else if (viewMode === 'month') {
      // Show last 30 days
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      return chartData.filter(item => new Date(item.date) >= thirtyDaysAgo);
    }
    // Default: show all data
    return chartData;
  };

  const filteredData = getFilteredData();

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex flex-col">
        <h2 className="text-xl font-bold mb-2">Camper Performance Metrics</h2>
        <div className="flex space-x-4 mb-4">
          <button 
            className={`px-4 py-2 rounded ${viewMode === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setViewMode('all')}
          >
            All Data
          </button>
          <button 
            className={`px-4 py-2 rounded ${viewMode === 'recent' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setViewMode('recent')}
          >
            Recent (7 Days)
          </button>
          <button 
            className={`px-4 py-2 rounded ${viewMode === 'month' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setViewMode('month')}
          >
            Last 30 Days
          </button>
        </div>
      </div>
      
      <div className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={filteredData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="displayDate" 
              label={{ value: 'Date', position: 'insideBottomRight', offset: -10 }}
            />
            <YAxis 
              domain={[0, 5]} 
              ticks={[0, 1, 2, 3, 4, 5]} 
              label={{ value: 'Score', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              formatter={(value, name) => {
                const formattedName = name
                  .replace('social_score', 'Social')
                  .replace('behavior_score', 'Behavior')
                  .replace('participation_score', 'Participation');
                return [value, formattedName];
              }}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Legend formatter={(value) => {
              return value
                .replace('social_score', 'Social')
                .replace('behavior_score', 'Behavior')
                .replace('participation_score', 'Participation');
            }} />
            <Line 
              type="monotone" 
              dataKey="social_score" 
              stroke="#8884d8" 
              strokeWidth={2}
              activeDot={{ r: 8 }}
              connectNulls={true}
            />
            <Line 
              type="monotone" 
              dataKey="behavior_score" 
              stroke="#82ca9d" 
              strokeWidth={2}
              activeDot={{ r: 8 }}
              connectNulls={true}
            />
            <Line 
              type="monotone" 
              dataKey="participation_score" 
              stroke="#ffc658" 
              strokeWidth={2}
              activeDot={{ r: 8 }}
              connectNulls={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4">
        <h3 className="text-lg font-semibold mb-2">Statistics</h3>
        <div className="grid grid-cols-3 gap-4">
          {['social_score', 'behavior_score', 'participation_score'].map(metric => {
            const values = filteredData.map(item => item[metric]).filter(val => val !== null);
            const avg = values.length ? (values.reduce((sum, val) => sum + val, 0) / values.length).toFixed(1) : 'N/A';
            const max = values.length ? Math.max(...values) : 'N/A';
            const min = values.length ? Math.min(...values) : 'N/A';
            
            return (
              <div key={metric} className="bg-gray-100 p-4 rounded">
                <h4 className="font-semibold">
                  {metric === 'social_score' ? 'Social' : 
                   metric === 'behavior_score' ? 'Behavior' : 'Participation'}
                </h4>
                <div className="grid grid-cols-3 gap-2 mt-2">
                  <div>
                    <div className="text-sm text-gray-500">Avg</div>
                    <div className="font-bold">{avg}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Max</div>
                    <div className="font-bold">{max}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Min</div>
                    <div className="font-bold">{min}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CamperScoresChart;