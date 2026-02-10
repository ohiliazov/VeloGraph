"use client";

import Link from "next/link";
import BikeSearch from "../components/BikeSearch";
import LanguageSwitcher from "../components/LanguageSwitcher";
import ThemeToggle from "../components/ThemeToggle";
import { useLanguage } from "../context/LanguageContext";

export default function Home() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
      <header className="max-w-4xl mx-auto px-6 mb-12 flex justify-between items-start relative z-40">
        <div>
          <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            VeloGraph
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 mt-2">
            {t.ui.hero_subtitle}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/fit"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-sm"
          >
            {/* Calculator icon */}
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="4" y="3" width="16" height="18" rx="2" ry="2" />
              <path d="M8 7h8M8 11h8M8 15h2M12 15h2M16 15h0" />
            </svg>
            Bike Fit Calculator
          </Link>
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </header>

      <main>
        <BikeSearch />
      </main>

      <footer className="max-w-4xl mx-auto px-6 mt-20 pt-8 border-t border-gray-200 dark:border-gray-800 text-center text-gray-400 dark:text-gray-500 text-sm">
        <p>© 2025 VeloGraph. {t.ui.footer_powered_by}</p>
      </footer>
    </div>
  );
}
