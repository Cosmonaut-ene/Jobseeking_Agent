import { createContext, useContext, useState } from 'react'
import { translations } from '../i18n/translations'
import type { Lang, TranslationKey } from '../i18n/translations'

const STORAGE_KEY = 'lang'

function detectLang(): Lang {
  const saved = localStorage.getItem(STORAGE_KEY) as Lang | null
  if (saved === 'en' || saved === 'zh') return saved
  return navigator.language.startsWith('zh') ? 'zh' : 'en'
}

interface LangCtx {
  lang: Lang
  toggle: () => void
  t: (key: TranslationKey) => string
}

const LanguageContext = createContext<LangCtx | null>(null)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>(detectLang)

  function toggle() {
    const next: Lang = lang === 'en' ? 'zh' : 'en'
    setLang(next)
    localStorage.setItem(STORAGE_KEY, next)
  }

  function t(key: TranslationKey): string {
    return translations[lang][key] as string
  }

  return (
    <LanguageContext.Provider value={{ lang, toggle, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLang() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLang must be used within LanguageProvider')
  return ctx
}

export function useT() {
  return useLang().t
}
