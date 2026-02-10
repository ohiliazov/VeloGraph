"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../context/LanguageContext";
import { supportedLanguages } from "../translations";

export default function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  const current = supportedLanguages.find((l) => l.code === language);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 focus:outline-none"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-lg" aria-hidden>
          {current?.flag ?? "🏳️"}
        </span>
        <span className="font-medium uppercase">{current?.code}</span>
      </button>

      {open && (
        <ul
          className="absolute right-0 z-50 mt-2 w-56 max-h-80 overflow-auto rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-1 shadow-lg"
          role="listbox"
        >
          {supportedLanguages.map((lang) => (
            <li key={lang.code}>
              <button
                className={`flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-800 ${
                  language === lang.code ? "bg-gray-50 dark:bg-gray-800" : ""
                }`}
                role="option"
                aria-selected={language === lang.code}
                onClick={() => {
                  setLanguage(lang.code);
                  setOpen(false);
                }}
              >
                <span className="text-lg" aria-hidden>
                  {lang.flag}
                </span>
                <span className="flex-1">
                  <span className="font-medium">{lang.name}</span>
                  <span className="ml-2 text-xs uppercase text-gray-500">
                    {lang.code}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
