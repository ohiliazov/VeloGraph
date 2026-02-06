"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { Language, translations, supportedLanguages } from "../translations";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: typeof translations.en;
}

const LanguageContext = createContext<LanguageContextType | undefined>(
  undefined,
);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const allowed = new Set(supportedLanguages.map((l) => l.code));

    const saved = localStorage.getItem("language");
    if (saved && allowed.has(saved as Language)) {
      setLanguageState(saved as Language);
      return;
    }

    const navLangs = (navigator.languages || [navigator.language])
      .filter(Boolean)
      .map((l) => (l || "").toLowerCase());

    for (const lang of navLangs) {
      const base = (lang.split("-")[0] || "").toLowerCase();
      if (base === "ru" || base === "be") continue; // explicitly exclude
      if (allowed.has(base as Language)) {
        setLanguageState(base as Language);
        return;
      }
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem("language", lang);
    }
  };

  const t = translations[language];

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
