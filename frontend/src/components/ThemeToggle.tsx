"use client";

import { useEffect, useState } from "react";

// Simple theme toggle that prefers stored user choice, otherwise system
// It toggles the `dark` class on <html> to force Tailwind dark styles
export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">();

  // Apply theme to <html>
  const applyTheme = (next: "light" | "dark") => {
    const root = document.documentElement;
    if (next === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    // Also reflect via CSS variables to align with globals.css usage
    const body = document.body as HTMLElement;
    if (next === "dark") {
      body.style.setProperty("--background", "#0a0a0a");
      body.style.setProperty("--foreground", "#ededed");
    } else {
      body.style.setProperty("--background", "#ffffff");
      body.style.setProperty("--foreground", "#171717");
    }
  };

  // Initialize from localStorage or system preference
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    const sysDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial: "light" | "dark" = saved ?? (sysDark ? "dark" : "light");
    setTheme(initial);
    applyTheme(initial);

    // React to system changes only if user hasn't explicitly chosen (i.e., no saved)
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      const hasSaved = !!localStorage.getItem("theme");
      if (!hasSaved) {
        const next: "light" | "dark" = e.matches ? "dark" : "light";
        setTheme(next);
        applyTheme(next);
      }
    };
    mql.addEventListener?.("change", onChange);
    return () => mql.removeEventListener?.("change", onChange);
  }, []);

  const toggle = () => {
    const next: "light" | "dark" = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("theme", next);
    }
    applyTheme(next);
  };

  return (
    <button
      onClick={toggle}
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 focus:outline-none"
      title="Toggle theme"
      aria-label="Toggle theme"
    >
      {/* Simple sun/moon inline icons */}
      <span className="w-4 h-4 inline-block" aria-hidden>
        {theme === "dark" ? (
          // Sun icon
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
          </svg>
        ) : (
          // Moon icon
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
          </svg>
        )}
      </span>
      <span className="text-xs font-medium">
        {theme === "dark" ? "Dark" : "Light"}
      </span>
    </button>
  );
}
