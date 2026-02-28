import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: '📊 Dashboard' },
  { to: '/scout', label: '🔍 Scout' },
  { to: '/scrapers', label: '🤖 Scrapers' },
  { to: '/jobs', label: '💼 Jobs' },
  { to: '/resume', label: '📄 Resume' },
  { to: '/profile', label: '👤 Profile' },
  { to: '/settings', label: '⚙️ Settings' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-base font-bold leading-tight">Jobseeking Agent</h1>
          <p className="text-xs text-gray-400 mt-0.5">AI-powered job hunt</p>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white font-medium'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
          v1.0.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 min-h-full">{children}</div>
      </main>
    </div>
  )
}
