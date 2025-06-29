import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Home, Users, Calendar, ArrowRight, Loader2, UserCheck, Baby } from 'lucide-react';

// Today's date constant - uses current date
const TODAY = new Date();

function UnitHeadBunkCard({ bunk, selectedDate }) {
  const [error, setError] = useState(null);

  // Format the date for URL - use selectedDate if provided, otherwise use today
  let formattedDate;
  if (selectedDate) {
    const year = selectedDate.getFullYear();
    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDate.getDate()).padStart(2, '0');
    formattedDate = `${year}-${month}-${day}`;
  } else {
    formattedDate = new Date().toISOString().split('T')[0];
  }

  return (
    <Link 
      to={`/bunk/${bunk.id}/${formattedDate}`} 
      className="group relative bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-sm hover:shadow-lg transition-all duration-300 rounded-2xl overflow-hidden hover:scale-[1.02] hover:-translate-y-1"
    >
      {/* Gradient header */}
      <div className="h-16 bg-gradient-to-r from-emerald-500 via-blue-500 to-purple-600 relative">
        <div className="absolute inset-0 bg-black/10"></div>
        {/* Decorative pattern */}
        <div className="absolute top-0 right-0 w-24 h-24 transform translate-x-12 -translate-y-12">
          <div className="w-full h-full rounded-full bg-white/10"></div>
        </div>
        <div className="absolute top-1 right-1 w-12 h-12 transform translate-x-6 -translate-y-6">
          <div className="w-full h-full rounded-full bg-white/5"></div>
        </div>
      </div>

      {/* Content */}
      <div className="relative px-4 pb-5 -mt-6">
        {/* Icon container */}
        <div className="flex justify-center mb-3">
          <div className="w-12 h-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <Home className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
          </div>
        </div>

        {/* Cabin name */}
        <div className="text-center mb-1">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
            {bunk.cabin_name}
          </h2>
          <div className="w-8 h-0.5 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full mx-auto"></div>
        </div>
        {/* Unit name */}
        <div className="text-center mb-2">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 italic">
            {bunk.unit_name}
          </span>
        </div>

        {/* Session info */}
        <div className="text-center mb-4">
          <div className="inline-flex items-center px-3 py-1 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/30">
            <Calendar className="w-3 h-3 text-blue-600 dark:text-blue-400 mr-1" />
            <span className="text-xs font-medium text-blue-700 dark:text-blue-300 truncate">
              {bunk.session_name}
            </span>
          </div>
        </div>

        {/* Stats row */}
        <div className="flex justify-between items-center mb-4 px-2">
          {/* Counselors count */}
          <div className="flex items-center space-x-1">
            <div className="w-8 h-8 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
              <UserCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="text-center">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {bunk.counselors?.length || 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Staff
              </div>
            </div>
          </div>

          {/* Campers count */}
          <div className="flex items-center space-x-1">
            <div className="w-8 h-8 bg-purple-50 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Baby className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="text-center">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {bunk.campers?.length || 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Campers
              </div>
            </div>
          </div>
        </div>

        {/* Counselor names - show first 2 */}
        {bunk.counselors && bunk.counselors.length > 0 && (
          <div className="text-center mb-3">
            <div className="text-xs text-gray-600 dark:text-gray-300 font-medium mb-1">
              Counselors:
            </div>
            {bunk.counselors.slice(0, 2).map((counselor, index) => (
              <div
                key={index}
                className="inline-block mx-1 px-2 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-xs font-medium border border-emerald-100 dark:border-emerald-800"
              >
                {counselor.first_name} {counselor.last_name}
              </div>
            ))}
            {bunk.counselors.length > 2 && (
              <div className="inline-block mx-1 px-2 py-1 rounded-full bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs">
                +{bunk.counselors.length - 2} more
              </div>
            )}
          </div>
        )}

        {/* Action indicator */}
        <div className="flex items-center justify-center">
          <div className="inline-flex items-center text-xs font-medium text-emerald-600 dark:text-emerald-400 group-hover:text-emerald-700 dark:group-hover:text-emerald-300 transition-colors">
            View Bunk
            <ArrowRight className="w-3 h-3 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      {/* Hover overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/5 to-blue-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    </Link>
  );
}

export default UnitHeadBunkCard;
