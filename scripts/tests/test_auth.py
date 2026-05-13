from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404

def test_auth_endpoints():
    # Test JWT token endpoint
    url = '/api/auth/token/'
    try:
        match = resolve(url)
        print(f'URL {url} resolves to: {match.view_name}')
    except Resolver404:
        print(f'URL {url} does not match any pattern')
    
    # Test token refresh endpoint
    url = '/api/auth/token/refresh/'
    try:
        match = resolve(url)
        print(f'URL {url} resolves to: {match.view_name}')
    except Resolver404:
        print(f'URL {url} does not match any pattern')

if __name__ == '__main__':
    test_auth_endpoints()
