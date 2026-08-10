import React, { useState } from 'react';

function SidebarLinkGroup({
  children,
  activecondition,
}) {

  const [open, setOpen] = useState(activecondition);

  const handleClick = () => {
    setOpen(!open);
  }

  return (
    <li className={`px-3 py-2 rounded-lg mb-0.5 last:mb-0 lg:px-1 lg:sidebar-expanded:px-3 2xl:px-3 bg-[linear-gradient(135deg,var(--tw-gradient-stops))] ${activecondition && 'from-violet-500/[0.12] dark:from-violet-500/[0.24] to-violet-500/[0.04]'}`}>
      {children(handleClick, open)}
    </li>
  );
}

export default SidebarLinkGroup;