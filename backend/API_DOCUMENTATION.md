# Orders CRUD API Documentation

This document describes the CRUD API endpoints for the Orders system in the BunkLogs application.

## Base URL
```
https://admin.bunklogs.net/api/
```

## Authentication
All endpoints require authentication. Include the authentication token in the request header:
```
Authorization: Token <your-token-here>
```

## Endpoints Overview

### Order Management
- `GET /api/orders/` - List all orders (filtered by user role)
- `POST /api/orders/` - Create a new order
- `GET /api/orders/{id}/` - Retrieve a specific order
- `PUT /api/orders/{id}/` - Update an order
- `PATCH /api/orders/{id}/` - Partially update an order
- `DELETE /api/orders/{id}/` - Delete an order

### Item Management
- `GET /api/items/` - List all available items
- `POST /api/items/` - Create a new item (staff only)
- `GET /api/items/{id}/` - Retrieve a specific item
- `PUT /api/items/{id}/` - Update an item (staff only)
- `PATCH /api/items/{id}/` - Partially update an item (staff only)
- `DELETE /api/items/{id}/` - Delete an item (staff only)

### Item Category Management
- `GET /api/item-categories/` - List all item categories
- `POST /api/item-categories/` - Create a new category (staff only)
- `GET /api/item-categories/{id}/` - Retrieve a specific category
- `PUT /api/item-categories/{id}/` - Update a category (staff only)
- `PATCH /api/item-categories/{id}/` - Partially update a category (staff only)
- `DELETE /api/item-categories/{id}/` - Delete a category (staff only)

### Order Type Management
- `GET /api/order-types/` - List all order types
- `POST /api/order-types/` - Create a new order type (staff only)
- `GET /api/order-types/{id}/` - Retrieve a specific order type
- `PUT /api/order-types/{id}/` - Update an order type (staff only)
- `PATCH /api/order-types/{id}/` - Partially update an order type (staff only)
- `DELETE /api/order-types/{id}/` - Delete an order type (staff only)

### Custom Endpoints
- `GET /api/order-types/{id}/items/` - Get available items for a specific order type
- `GET /api/order-statistics/` - Get order statistics (counts by status)

## Data Models

### Order
```json
{
  "id": 1,
  "user": 1,
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "order_date": "2025-05-27T12:00:00Z",
  "order_status": "pending",
  "order_status_display": "Pending",
  "order_bunk": 1,
  "order_bunk_name": "Cabin A1",
  "order_type": 1,
  "order_type_name": "Supply Order",
  "order_items": [
    {
      "id": 1,
      "item": 1,
      "item_name": "Notebook",
      "item_description": "Spiral notebook",
      "item_quantity": 5
    }
  ]
}
```

### Item
```json
{
  "id": 1,
  "item_name": "Notebook",
  "item_description": "Spiral notebook for camp activities",
  "available": true,
  "item_category": 1,
  "item_category_name": "Stationery"
}
```

### Item Category
```json
{
  "id": 1,
  "category_name": "Stationery",
  "category_description": "Writing and office supplies"
}
```

### Order Type
```json
{
  "id": 1,
  "type_name": "Supply Order",
  "type_description": "Request for camp supplies",
  "item_categories": [
    {
      "id": 1,
      "category_name": "Stationery",
      "category_description": "Writing and office supplies"
    }
  ]
}
```

## Creating a New Order

To create a new order, send a POST request to `/api/orders/` with the following structure:

```json
{
  "order_status": "pending",
  "order_bunk": 1,
  "order_type": 1,
  "order_items": [
    {
      "item": 1,
      "item_quantity": 5
    },
    {
      "item": 2,
      "item_quantity": 3
    }
  ]
}
```

## Query Parameters

### Orders
- `?status=pending` - Filter orders by status
- `?order_type=1` - Filter orders by order type
- `?user=1` - Filter orders by user (staff only)

### Items
- `?category=1` - Filter items by category
- `?available=true` - Filter by availability

## Order Status Choices
- `pending` - Pending
- `approved` - Approved
- `in_progress` - In Progress
- `completed` - Completed
- `cancelled` - Cancelled

## Permission Levels

### Regular Users (Counselors)
- Can view only their own orders
- Can create new orders
- Can update their pending orders
- Can view all items and categories

### Staff Users (Unit Heads, Directors)
- Can view all orders
- Can update any order status
- Can create, update, and delete items, categories, and order types
- Can access order statistics

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message describing the validation issue"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

## Frontend Implementation Notes

1. **Authentication**: Use token-based authentication for all API calls
2. **Role-based UI**: Hide create/edit/delete buttons for items/categories/order-types from non-staff users
3. **Order Status**: Show appropriate actions based on order status and user role
4. **Real-time Updates**: Consider implementing WebSocket or polling for order status updates
5. **Validation**: Implement client-side validation that matches the API validation rules

## Testing the API

Use the provided test script (`test_orders_api.py`) to verify all endpoints are working correctly. The script will test all endpoints and show the expected authentication responses.
