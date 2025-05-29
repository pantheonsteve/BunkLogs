import React, { useState } from 'react';

function OrdersTableItem(props) {

  const [descriptionOpen, setDescriptionOpen] = useState(false);

  const statusColor = (status) => {
    switch (status) {
      case 'Approved':
        return 'bg-green-500/20 text-green-700';
      case 'Refunded':
        return 'bg-yellow-500/20 text-yellow-700';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400';
    }
  };

  const typeIcon = (type) => {
    switch (type) {
      case 'Subscription':
        return (
          <svg className="fill-current text-gray-400 dark:text-gray-500 shrink-0 mr-2" width="16" height="16" viewBox="0 0 16 16">
            <path d="M4.3 4.5c1.9-1.9 5.1-1.9 7 0 .7.7 1.2 1.7 1.4 2.7l2-.3c-.2-1.5-.9-2.8-1.9-3.8C10.1.4 5.7.4 2.9 3.1L.7.9 0 7.3l6.4-.7-2.1-2.1zM15.6 8.7l-6.4.7 2.1 2.1c-1.9 1.9-5.1 1.9-7 0-.7-.7-1.2-1.7-1.4-2.7l-2 .3c.2 1.5.9 2.8 1.9 3.8 1.4 1.4 3.1 2 4.9 2 1.8 0 3.6-.7 4.9-2l2.2 2.2.8-6.4z" />
          </svg>
        );
      default:
        return (
          <svg className="fill-current text-gray-400 dark:text-gray-500 shrink-0 mr-2" width="16" height="16" viewBox="0 0 16 16">
            <path d="M11.4 0L10 1.4l2 2H8.4c-2.8 0-5 2.2-5 5V12l-2-2L0 11.4l3.7 3.7c.2.2.4.3.7.3.3 0 .5-.1.7-.3l3.7-3.7L7.4 10l-2 2V8.4c0-1.7 1.3-3 3-3H12l-2 2 1.4 1.4 3.7-3.7c.4-.4.4-1 0-1.4L11.4 0z" />
          </svg>
        );
    }
  };

  return (
    <tbody className="text-sm">
      {/* Row */}
      <tr>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap w-px">
          <div className="flex items-center">
            <label className="inline-flex">
              <span className="sr-only">Select</span>
              <input id={props.id} className="form-checkbox" type="checkbox" onChange={props.handleClick} checked={props.isChecked} />
            </label>
          </div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="flex items-center text-gray-800">
            <div className="font-medium text-sky-600">{props.order}</div>
          </div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div>{props.date}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="flex items-center">
            <div className="text-gray-800 dark:text-gray-100">{props.bunk}</div>
          </div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="font-medium text-gray-800 dark:text-gray-100">{props.customer}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className={`inline-flex font-medium rounded-full text-center px-2.5 py-0.5 ${statusColor(props.status)}`}>{props.status}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="text-center">{props.items}</div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
          <div className="flex items-center">
            {typeIcon(props.type)}
            <div>{props.type}</div>
          </div>
        </td>
        <td className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap w-px">
          <div className="flex items-center">
            <button
              className={`text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400 ${descriptionOpen && 'rotate-180'}`}
              aria-expanded={descriptionOpen}
              onClick={() => setDescriptionOpen(!descriptionOpen)}
              aria-controls={`description-${props.id}`}
            >
              <span className="sr-only">Menu</span>
              <svg className="w-8 h-8 fill-current" viewBox="0 0 32 32">
                <path d="M16 20l-5.4-5.4 1.4-1.4 4 4 4-4 1.4 1.4z" />
              </svg>
            </button>
          </div>
        </td>
      </tr>
      {/*
      Example of content revealing when clicking the button on the right side:
      Note that you must set a "colSpan" attribute on the <td> element,
      and it should match the number of columns in your table
      */}
      <tr id={`description-${props.id}`} role="region" className={`${!descriptionOpen && 'hidden'}`}>
        <td colSpan="8" className="px-2 first:pl-5 last:pr-5 py-3">
          <div className="bg-gray-50 dark:bg-gray-950/[0.15] p-4 -mt-3">            
            {props.order_items && props.order_items.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-800 dark:text-gray-100 mb-3">Items Requested</h4>
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-900/50">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Item</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Description</th>
                        <th className="px-4 py-3 text-center font-medium text-gray-600 dark:text-gray-400">Quantity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {props.order_items.map((item, index) => (
                        <tr key={item.id || index} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-100">
                            {item.item_name}
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                            {item.item_description}
                          </td>
                          <td className="px-4 py-3 text-center font-medium text-gray-800 dark:text-gray-100">
                            {item.item_quantity}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </td>
      </tr>
    </tbody>
  );
}

export default OrdersTableItem;
