import { useState } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useLocation } from 'react-router-dom';


function BunkTile({ cabin, session, bunk_id, counselors}) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(null);

  return (
    <div className="grid grid-cols-1 gap-6">
      {/* Bunk Tile */}
      <Link to={`/bunk/${bunk_id}`} className="relative col-span-full xl:col-span-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-xs rounded-lg">
    <div className="relative col-span-full xl:col-span-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-xs rounded-b-lg">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-green-500" aria-hidden="true"></div>
            <div className="px-5 pt-5 pb-6 border-b border-gray-200 dark:border-gray-700/60">
                <header className="flex items-center mb-2">
                    <div className="w-6 h-6 rounded-full shrink-0 bg-green-500 mr-3">
                        <svg className="w-6 h-6 fill-current text-white" viewBox="0 0 24 24">
                        <path d="M12 17a.833.833 0 01-.833-.833 3.333 3.333 0 00-3.334-3.334.833.833 0 110-1.666 3.333 3.333 0 003.334-3.334.833.833 0 111.666 0 3.333 3.333 0 003.334 3.334.833.833 0 110 1.666 3.333 3.333 0 00-3.334 3.334c0 .46-.373.833-.833.833z" />
                        </svg>
                    </div>
                    <h3 className="text-lg text-gray-800 dark:text-gray-100 font-semibold">{cabin} {session}</h3>
                    <p>{counselors}</p>
                </header>
                {/* Price */}
                <div className="text-gray-800 dark:text-gray-100 font-bold mb-4">
                </div>
            {/* CTA */}
            <button className="btn border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300 w-full">Downgrade</button>
        </div>
        </div>
        </Link>
    </div>
  );
}
export default BunkTile;