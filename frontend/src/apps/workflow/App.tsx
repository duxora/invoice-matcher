import { NavLink, Routes, Route } from 'react-router-dom'
import type { ReactNode } from 'react'
import TaskBoard from './components/TaskBoard'
import PipelinesPage from './pages/PipelinesPage'
import SessionsPage from './pages/SessionsPage'

interface TabLinkProps {
  to: string
  end?: boolean
  children: ReactNode
}

function TabLink({ to, end, children }: TabLinkProps) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `px-3 py-1.5 text-xs font-medium rounded transition-colors ${
          isActive
            ? 'bg-gray-800 text-white'
            : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

export default function WorkflowApp() {
  return (
    <div className="flex flex-col h-full">
      {/* Sub-nav tabs */}
      <nav className="flex items-center gap-1 px-4 py-1.5 border-b border-gray-800 shrink-0 bg-gray-950">
        <TabLink to="/workflow" end>Tasks</TabLink>
        <TabLink to="/workflow/pipelines">Pipelines</TabLink>
        <TabLink to="/workflow/sessions">Sessions</TabLink>
      </nav>

      {/* Sub-route content */}
      <div className="flex-1 min-h-0">
        <Routes>
          <Route index element={<TaskBoard />} />
          <Route path="pipelines" element={<PipelinesPage />} />
          <Route path="sessions" element={<SessionsPage />} />
        </Routes>
      </div>
    </div>
  )
}
