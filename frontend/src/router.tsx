import { createBrowserRouter, Navigate } from 'react-router-dom'
import { lazy } from 'react'
import HubShell from './layouts/HubShell'
import PlaceholderApp from './shared/PlaceholderApp'

const WorkflowApp = lazy(() => import('./apps/workflow/App'))

export const router = createBrowserRouter([
  {
    element: <HubShell />,
    children: [
      { index: true, element: <Navigate to="/workflow" replace /> },
      {
        path: 'workflow/*',
        element: <WorkflowApp />,
      },
      {
        path: 'scheduler/*',
        element: <PlaceholderApp appName="Scheduler" jinjaPath="/scheduler" />,
      },
      {
        path: 'kb/*',
        element: <PlaceholderApp appName="Knowledge Base" jinjaPath="/kb" />,
      },
      {
        path: 'telegram-bridge/*',
        element: <PlaceholderApp appName="Telegram Bridge" jinjaPath="/telegram-bridge" />,
      },
    ],
  },
])
