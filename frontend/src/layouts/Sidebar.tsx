import { NavLink } from 'react-router-dom'
import { HUB_APPS } from '../shared/apps'
import { theme } from '../shared/theme'

export default function Sidebar() {
  return (
    <aside
      className={`w-56 min-h-screen flex flex-col ${theme.sidebar.bg} ${theme.sidebar.border} border-r shrink-0`}
    >
      {/* Brand */}
      <div className={`px-4 py-5 border-b ${theme.sidebar.border}`}>
        <span className={`text-sm font-semibold tracking-wide uppercase ${theme.sidebar.textActive}`}>
          Automation Hub
        </span>
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3">
        <ul className="space-y-0.5 px-2">
          {HUB_APPS.map((app) => {
            const label = (
              <>
                <span className="text-base leading-none" aria-hidden="true">
                  {app.icon}
                </span>
                <span className="text-sm font-medium">{app.name}</span>
              </>
            )

            const baseClasses = `flex items-center gap-3 w-full rounded-md px-3 py-2 transition-colors ${theme.sidebar.hover}`

            if (app.migrated) {
              return (
                <li key={app.id}>
                  <NavLink
                    to={app.path}
                    className={({ isActive }) =>
                      `${baseClasses} ${
                        isActive
                          ? `${theme.sidebar.activeBg} ${theme.sidebar.textActive}`
                          : theme.sidebar.text
                      }`
                    }
                    aria-label={app.description}
                  >
                    {label}
                  </NavLink>
                </li>
              )
            }

            return (
              <li key={app.id}>
                <a
                  href={app.path}
                  className={`${baseClasses} ${theme.sidebar.text}`}
                  aria-label={app.description}
                >
                  {label}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
