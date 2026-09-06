import React, { createContext, useContext, useState, useEffect } from "react";
import { translations } from "../utils/translations";
import type { TranslationKey, Language } from "../utils/translations";
export type { Language };

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Language>(() => {
    try {
      const saved = localStorage.getItem("sih_lang");
      return saved === "hi" ? "hi" : "en";
    } catch {
      return "en";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("sih_lang", lang);
    } catch {
      // ignore
    }
  }, [lang]);

  const toggleLang = () => {
    setLang((prev) => (prev === "en" ? "hi" : "en"));
  };

  const t = (key: TranslationKey): string => {
    const dict = translations[lang] || translations.en;
    return dict[key] || translations.en[key] || String(key);
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    // Fallback if not wrapped in LanguageProvider
    return {
      lang: "en" as Language,
      setLang: () => {},
      toggleLang: () => {},
      t: (key: TranslationKey) => translations.en[key] || String(key),
    };
  }
  return context;
}
