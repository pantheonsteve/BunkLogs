import { useState, useEffect } from 'react'
import { AuthChangeRedirector, AnonymousRoute, AuthenticatedRoute } from './auth/routing'
import {
  createBrowserRouter,
  RouterProvider
} from 'react-router-dom'
import Signin from './pages/Signin'
import ProviderCallback from './socialaccount/ProviderCallback'
// import Calculator from './Calculator'
import Root from './Root'
import { useConfig } from './auth/hooks'

function createRouter(config) {
  return createBrowserRouter([
    {
      path: '/',
      element: <Root />,
      children: [
        // ... other routes
        {
          path: '/account/provider/callback',
          element: <ProviderCallback />
        },
        {
          path: '/signin',
          element: <AnonymousRoute><Signin /></AnonymousRoute>
        },
        // ... other routes
      ]
    }
  ]);
}

export default function Router () {
  // If we create the router globally, the loaders of the routes already trigger
  // even before the <AuthContext/> trigger the initial loading of the auth.
  // state.
  const [router, setRouter] = useState(null)
  const config = useConfig()
  useEffect(() => {
    setRouter(createRouter(config))
  }, [config])
  return router ? <RouterProvider router={router} /> : null
}