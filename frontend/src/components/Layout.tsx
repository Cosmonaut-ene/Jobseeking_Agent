import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, Globe, Bell,
  User, FileText, Settings, Sun, Moon, BarChart3,
} from 'lucide-react'
import { useLang, useT } from '../contexts/LanguageContext'
import { useTheme } from '../contexts/ThemeContext'
import type { TranslationKey } from '../i18n/translations'

const NAV_ITEMS: { to: string; key: TranslationKey; Icon: React.ElementType }[] = [
  { to: '/',              key: 'nav_dashboard',     Icon: LayoutDashboard },
  { to: '/jobs',          key: 'nav_jobs',           Icon: Briefcase       },
  { to: '/analytics',     key: 'nav_analytics',      Icon: BarChart3       },
  { to: '/scrapers',      key: 'nav_scrapers',       Icon: Globe           },
  { to: '/notifications', key: 'nav_notifications',  Icon: Bell            },
  { to: '/profile',       key: 'nav_profile',        Icon: User            },
  { to: '/resume',        key: 'nav_resume',         Icon: FileText        },
  { to: '/settings',      key: 'nav_settings',       Icon: Settings        },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const t = useT()
  const { lang, toggle: toggleLang } = useLang()
  const { theme, toggle: toggleTheme } = useTheme()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar — always dark. Collapses to an icon-only rail below md:
          this app has no mobile-first target (it's headed for a desktop
          package, per SPEC 附录 F.8), so a full slide-out drawer would be
          more machinery than the payoff justifies — but the fixed 208px
          rail was eating over half of a phone-width viewport with no
          way to shrink it at all, which was a real problem on its own. */}
      <aside
        className="w-16 md:w-52 flex flex-col shrink-0 border-r border-white/[0.06]"
        style={{ background: 'linear-gradient(180deg, #27272a 0%, #18181b 45%, #0f0f11 100%)' }}
      >
        {/* Brand */}
        <div className="px-2 md:px-4 py-5 border-b border-white/[0.07]">
          <div className="flex items-center justify-center md:justify-start gap-2.5">
            <div className="w-1.5 h-5 rounded-full bg-amber-400 shrink-0 shadow-[0_0_8px_rgba(251,191,36,0.5)]" />
            <div className="hidden md:block">
              <h1 className="text-sm font-semibold text-white leading-tight tracking-tight">{t('appName')}</h1>
              <p className="text-[10px] text-zinc-500 mt-0.5">{t('appSubtitle')}</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-px">
          {NAV_ITEMS.map(({ to, key, Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} title={t(key)}>
              {({ isActive }) => (
                <div className={`flex items-center justify-center md:justify-start gap-2.5 px-2.5 py-[7px] rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-white/[0.09] text-amber-300 font-medium'
                    : 'text-zinc-500 hover:bg-white/[0.05] hover:text-zinc-200'
                }`}>
                  <span className={`hidden md:block w-[3px] h-3.5 rounded-full shrink-0 transition-all duration-200 ${
                    isActive ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]' : 'bg-zinc-700'
                  }`} />
                  <Icon size={16} strokeWidth={isActive ? 2 : 1.6} className="shrink-0" />
                  <span className="hidden md:inline">{t(key)}</span>
                </div>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 py-3 border-t border-white/[0.07] flex flex-col md:flex-row items-center justify-between gap-1.5">
          <span className="hidden md:inline text-[10px] text-zinc-600">v1.0.0</span>
          <div className="flex items-center gap-1.5">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-md text-zinc-500 hover:text-amber-400 hover:bg-white/[0.06] transition-colors"
              title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
            >
              {theme === 'dark'
                ? <Sun size={13} />
                : <Moon size={13} />}
            </button>
            {/* Language toggle */}
            <button
              onClick={toggleLang}
              className="px-1.5 py-0.5 rounded text-[11px] text-zinc-500 hover:text-amber-400 transition-colors"
            >
              {lang === 'en' ? '中文' : 'EN'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 min-h-full">{children}</div>
      </main>
    </div>
  )
}
