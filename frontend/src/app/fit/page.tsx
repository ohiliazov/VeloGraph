"use client";

import React from "react";
import BikeFitCalculator from "@/components/BikeFitCalculator";

export default function FitCalculatorPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
      <header className="max-w-5xl mx-auto px-6 mb-10 flex items-center justify-between">
        <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
          Fit Calculator
        </h1>
        <a href="/" className="text-sm text-blue-500 hover:underline">
          Home
        </a>
      </header>

      <main>
        <BikeFitCalculator />
      </main>

      <footer className="max-w-5xl mx-auto px-6 mt-16 pt-8 border-t border-gray-200 dark:border-gray-800 text-center text-gray-400 dark:text-gray-500 text-sm">
        <p>© 2025 VeloGraph. Fit smarter, ride faster.</p>
      </footer>
    </div>
  );
}
