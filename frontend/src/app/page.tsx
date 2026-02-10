"use client";

import BikeSearch from "../components/BikeSearch";
import LanguageSwitcher from "../components/LanguageSwitcher";
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
        <LanguageSwitcher />
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
