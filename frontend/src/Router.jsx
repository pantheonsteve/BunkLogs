import { RouterProvider } from 'react-router-dom';
import { createBrowserRouter } from '@datadog/browser-rum-react/react-router-v7';
import { RootLayout } from './routes/guards';
import { routeConfig } from './routes/routeConfig';

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: routeConfig,
  },
]);

export default function Router() {
  return <RouterProvider router={router} />;
}
