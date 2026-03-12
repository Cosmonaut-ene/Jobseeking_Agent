import { NavLink } from 'react-router-dom'
import { useLang, useT } from '../contexts/LanguageContext'
import type { TranslationKey } from '../i18n/translations'

const NAV_ITEMS: { to: string; key: TranslationKey }[] = [
  { to: '/', key: 'nav_dashboard' },
  { to: '/jobs', key: 'nav_jobs' },
  { to: '/scrapers', key: 'nav_scrapers' },
  { to: '/notifications', key: 'nav_notifications' },
  { to: '/profile', key: 'nav_profile' },
  { to: '/resume', key: 'nav_resume' },
  { to: '/settings', key: 'nav_settings' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const t = useT()
  const { lang, toggle } = useLang()

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-base font-bold leading-tight">{t('appName')}</h1>
          <p className="text-xs text-gray-400 mt-0.5">{t('appSubtitle')}</p>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
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
              {t(item.key)}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-700 text-xs text-gray-500 flex items-center justify-between">
          <span>v1.0.0</span>
          <button
            onClick={toggle}
            className="px-2 py-0.5 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white transition-colors text-xs"
          >
            {lang === 'en' ? '中文' : 'EN'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 min-h-full">{children}</div>
      </main>
    </div>
  )
}
