import React, { useState, useEffect } from 'react';
import Orders from './OrdersTableItem';

import Image01 from '../../images/icon-01.svg';
import Image02 from '../../images/icon-02.svg';
import Image03 from '../../images/icon-03.svg';

function OrdersTable({
  selectedItems,
  data,
  onOrderUpdate
}) {

  console.log('Orders table received data:', data);

  const [selectAll, setSelectAll] = useState(false);
  const [isCheck, setIsCheck] = useState([]);
  const [list, setList] = useState([]);

  // Transform API data to match the expected format for the table
  const transformOrderData = (orders) => {
    return orders.map(order => ({
      id: order.id.toString(),
      image: Image01, // You might want to assign different images based on order type
      order: `#${order.id}`,
      date: new Date(order.order_date).toLocaleDateString('en-US', {
        month: 'long',
        day: '2-digit',
        year: 'numeric',
      }),
      customer: order.user_name,
      total: `$${order.order_items?.reduce((sum, item) => sum + (item.item_quantity * 10), 0).toFixed(2)}`, // Estimated total since we don't have pricing
      status: order.order_status_display,
      rawStatus: order.order_status, // Keep the raw status for the API
      bunk: order.order_bunk_cabin,
      items: order.order_items?.length.toString() || '0',
      order_items: order.order_items || [],
      location: order.order_bunk_name,
      type: order.order_type_name,
      description: `${order.order_items?.map(item => item.item_description).join(', ')} from ${order.order_bunk_name}`
    }));
  };

  const handleStatusUpdate = (orderId, newStatus, updatedOrder) => {
    // Update the local list
    setList(prevList => 
      prevList.map(order => 
        order.id === orderId.toString() 
          ? { 
              ...order, 
              status: updatedOrder.order_status_display,
              rawStatus: updatedOrder.order_status
            }
          : order
      )
    );

    // Call parent callback if provided
    if (onOrderUpdate) {
      onOrderUpdate(orderId, newStatus, updatedOrder);
    }
  };

  useEffect(() => {
    if (data && Array.isArray(data)) {
      const transformedData = transformOrderData(data);
      setList(transformedData);
    }
  }, [data]);

  const handleSelectAll = () => {
    setSelectAll(!selectAll);
    setIsCheck(list.map(li => li.id));
    if (selectAll) {
      setIsCheck([]);
    }
  };

  const handleClick = e => {
    const { id, checked } = e.target;
    setSelectAll(false);
    setIsCheck([...isCheck, id]);
    if (!checked) {
      setIsCheck(isCheck.filter(item => item !== id));
    }
  };

  useEffect(() => {
    selectedItems(isCheck);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCheck]);

  return (
    <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl relative">
      <header className="px-5 py-4">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">All Orders <span className="text-gray-400 dark:text-gray-500 font-medium">{list.length}</span></h2>
      </header>
      <div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="table-auto w-full dark:text-gray-300 divide-y divide-gray-100 dark:divide-gray-700/60">
            {/* Table header */}
            <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20 border-t border-gray-100 dark:border-gray-700/60">
              <tr>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap w-px">
                  <div className="flex items-center">
                    <label className="inline-flex">
                      <span className="sr-only">Select all</span>
                      <input className="form-checkbox" type="checkbox" checked={selectAll} onChange={handleSelectAll} />
                    </label>
                  </div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Order #</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Date</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Bunk</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Counselor</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Status</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold">Items</div>
                </th>
                <th className="px-2 first:pl-5 last:pr-5 py-3 whitespace-nowrap">
                  <div className="font-semibold text-left">Order Type</div>
                </th>
              </tr>
            </thead>
            {/* Table body */}
            {list.length > 0 ? (
              list.map(order => {
                return (
                  <Orders
                    key={order.id}
                    id={order.id}
                    image={order.image}
                    order={order.order}
                    date={order.date}
                    customer={order.customer}
                    status={order.status}
                    bunk={order.bunk}
                    items={order.items}
                    order_items={order.order_items}
                    type={order.type}
                    description={order.description}
                    rawStatus={order.rawStatus}
                    handleClick={handleClick}
                    isChecked={isCheck.includes(order.id)}
                    onStatusUpdate={handleStatusUpdate}
                  />
                )
              })
            ) : (
              <tbody>
                <tr>
                  <td colSpan="10" className="px-2 first:pl-5 last:pr-5 py-8 text-center">
                    <div className="text-gray-500 dark:text-gray-400">
                      <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p>No orders found</p>
                    </div>
                  </td>
                </tr>
              </tbody>
            )}
          </table>

        </div>
      </div>
    </div>
  );
}

export default OrdersTable;
