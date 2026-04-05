import { Outlet } from 'react-router-dom'
import { Suspense } from 'react'
import Sidebar from './Sidebar'
import { theme } from '../shared/theme'

export default function HubShell() {
  return (
    <div className={`flex min-h-screen ${theme.shell.bg} ${theme.shell.text}`}>
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Suspense fallback={<div className="p-6 text-gray-500 text-sm">Loading...</div>}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
