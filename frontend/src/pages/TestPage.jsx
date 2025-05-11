import React, { useState } from 'react';

function TestPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    
    return (
        <div className="flex h-[100dvh] overflow-hidden">
        {/* Sidebar */}
        <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
            {/* Sidebar content */}
        </div>
    
        {/* Content area */}
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
            {/* Site header */}
            <header>
            <button onClick={() => setSidebarOpen(!sidebarOpen)}>Toggle Sidebar</button>
            </header>
    
            <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Test Page</h1>
            </div>
            </main>
        </div>
        </div>
    );
}
export default TestPage;