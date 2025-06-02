import React from 'react';
import { User, Mail, Shield } from 'lucide-react';

const UserProfile = ({ user }) => {
  // Sample user data - replace with your actual user data

  return (
    <div className="w-full bg-white rounded-2xl shadow-sm border border-gray-100 mb-5">
      {/* Header gradient background */}
      {/* <div className="h-32 bg-gradient-to-r from-blue-200 via-purple-300 to-blue-300"></div> */}
      
      {/* Profile content */}
      <div className="relative px-8 pb-8">
        {/* Profile image - positioned to overlap the header */}
        <div className="flex justify-center">
          <div className="relative -mt-16 mb-6">
            <div className="w-32 h-32 rounded-full bg-white p-1 shadow-lg">
              {user.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.name}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <div className="w-full h-full rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                  <User className="w-12 h-12 text-gray-400" />
                </div>
              )}
            </div>
            {/* Online status indicator */}
            <div className="absolute bottom-2 right-2 w-6 h-6 bg-green-500 rounded-full border-3 border-white shadow-sm"></div>
          </div>
        </div>

        {/* User information */}
        <div className="text-center space-y-4">
          {/* Name */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{user.first_name} {user.last_name}</h1>
            <div className="w-16 h-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto"></div>
          </div>

          {/* Role */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full border border-blue-100">
            <Shield className="w-4 h-4" />
            <span className="font-medium text-sm">{user.role}</span>
          </div>

          {/* Email */}
          <div className="flex items-center justify-center gap-2 text-gray-600">
            <Mail className="w-4 h-4" />
            <span className="text-sm font-medium">{user.email}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;