"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useComparison } from "@/context/ComparisonContext";
import LanguageSwitcher from "../../components/LanguageSwitcher";
import BikeFrameSVG from "../../components/BikeFrameSVG";
import { GeometrySpec } from "@/types";

export default function ComparisonPage() {
  const { t } = useLanguage();
  const { comparisonList, removeFromCompare, clearComparison } =
    useComparison();
  const [showOnlyDifferences, setShowOnlyDifferences] = useState(false);

  if (comparisonList.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-3xl font-bold mb-8 dark:text-white">
            {t.ui.comparison}
          </h1>
          <p className="mb-8 text-gray-600 dark:text-gray-400">
            {t.ui.no_bikes_to_compare}
          </p>
          <Link
            href="/"
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            ← {t.ui.back_to_search}
          </Link>
        </div>
      </div>
    );
  }

  const geometryKeys: (keyof GeometrySpec)[] = [
    "stack_mm",
    "reach_mm",
    "top_tube_effective_mm",
    "seat_tube_length_mm",
    "head_tube_length_mm",
    "chainstay_length_mm",
    "head_tube_angle",
    "seat_tube_angle",
    "bb_drop_mm",
    "wheelbase_mm",
  ];

  const isDifferent = (key: keyof GeometrySpec) => {
    if (comparisonList.length < 2) return false;
    const firstValue = comparisonList[0].geometry[key];
    return comparisonList.some((item) => item.geometry[key] !== firstValue);
  };

  const filteredKeys = showOnlyDifferences
    ? geometryKeys.filter(isDifferent)
    : geometryKeys;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex justify-between items-center mb-8">
          <Link
            href="/"
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            ← {t.ui.back_to_search}
          </Link>
          <div className="flex items-center gap-4">
            <LanguageSwitcher />
            <button
              onClick={clearComparison}
              className="text-red-600 dark:text-red-400 hover:underline text-sm font-medium"
            >
              {t.ui.clear_comparison}
            </button>
          </div>
        </div>

        <div className="flex justify-between items-end mb-6">
          <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white">
            {t.ui.comparison} ({comparisonList.length})
          </h1>
          <label className="flex items-center gap-2 cursor-pointer bg-white dark:bg-gray-900 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm">
            <input
              type="checkbox"
              checked={showOnlyDifferences}
              onChange={(e) => setShowOnlyDifferences(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t.ui.show_only_differences}
            </span>
          </label>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 uppercase text-xs font-semibold border-b dark:border-gray-800">
                  <th className="py-4 px-6 border-r dark:border-gray-800 sticky left-0 bg-gray-50 dark:bg-gray-800 z-10 w-48">
                    {t.ui.metadata}
                  </th>
                  {comparisonList.map((item, idx) => (
                    <th
                      key={idx}
                      className="py-4 px-6 min-w-[200px] border-r dark:border-gray-800"
                    >
                      <div className="flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="text-gray-900 dark:text-white font-bold normal-case text-base">
                              {item.geometry.definition?.brand_name}{" "}
                              {item.geometry.definition?.model_name}
                            </p>
                            <p className="text-gray-500 dark:text-gray-400 font-medium normal-case">
                              {t.geometry.size_label}:{" "}
                              {item.geometry.size_label}
                            </p>
                          </div>
                          <button
                            onClick={() => removeFromCompare(item.geometry.id)}
                            className="text-red-400 hover:text-red-600 p-1"
                          >
                            ✕
                          </button>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded p-2 flex justify-center">
                          <BikeFrameSVG geometry={item.geometry} height={70} />
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {/* Basic Info */}
                <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="py-3 px-6 font-medium text-gray-500 dark:text-gray-400 bg-gray-50/30 dark:bg-gray-800/10 border-r dark:border-gray-800 sticky left-0 z-10">
                    {t.ui.material}
                  </td>
                  {comparisonList.map((item, idx) => (
                    <td
                      key={idx}
                      className="py-3 px-6 border-r dark:border-gray-800 text-xs dark:text-gray-300"
                    >
                      {item.geometry.definition?.material || "-"}
                    </td>
                  ))}
                </tr>

                {/* Geometry Params */}
                {filteredKeys.map((key) => (
                  <tr
                    key={key}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="py-3 px-6 font-medium text-gray-900 dark:text-gray-200 bg-gray-50/50 dark:bg-gray-800/20 border-r dark:border-gray-800 sticky left-0 z-10">
                      {t.geometry[key as keyof typeof t.geometry]}
                    </td>
                    {comparisonList.map((item, idx) => (
                      <td
                        key={idx}
                        className={`py-3 px-6 border-r dark:border-gray-800 font-mono ${
                          isDifferent(key)
                            ? "text-blue-600 dark:text-blue-400 font-bold"
                            : "text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        {
                          item.geometry[key as keyof typeof item.geometry] as
                            | string
                            | number
                        }
                        {String(key).includes("angle") ? "°" : " mm"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
