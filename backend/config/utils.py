"""
Utility functions for Django settings and DRF Spectacular customization.
"""

def custom_operation_id_generator(path, method):
    """
    Custom operation ID generator to avoid collisions between similar endpoints.
    """
    # Remove leading/trailing slashes and split the path
    path_parts = path.strip('/').split('/')
    
    # Handle specific collision cases
    if 'auth-token' in path_parts:
        # DRF's obtain_auth_token endpoint
        if method.lower() == 'post':
            return 'obtainAuthToken'
    elif 'auth' in path_parts and 'token' in path_parts:
        # JWT token endpoints
        if method.lower() == 'post':
            return 'jwtTokenCreate'
        elif method.lower() == 'patch':
            return 'jwtTokenRefresh'
        elif method.lower() == 'get':
            return 'jwtTokenVerify'
    
    # Default behavior for other endpoints
    method_name = method.lower()
    if method_name == 'get':
        action = 'retrieve' if '{id}' in path or '{pk}' in path else 'list'
    elif method_name == 'post':
        action = 'create'
    elif method_name == 'put':
        action = 'update'
    elif method_name == 'patch':
        action = 'partialUpdate'
    elif method_name == 'delete':
        action = 'destroy'
    else:
        action = method_name
    
    # Create operation ID from path parts
    resource_name = ''.join(word.capitalize() for word in path_parts if word not in ['api', 'v1'])
    
    # Remove common suffixes for cleaner names
    resource_name = resource_name.replace('List', '').replace('Create', '').replace('Update', '').replace('Delete', '')
    
    return f'{resource_name}{action.capitalize()}'
