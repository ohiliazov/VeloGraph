"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useComparison } from "@/context/ComparisonContext";
import LanguageSwitcher from "../../components/LanguageSwitcher";
import BikeFrameSVG from "../../components/BikeFrameSVG";
import { Geometry } from "@/types";

export default function ComparisonPage() {
  const { t } = useLanguage();
  const { comparisonList, removeFromCompare, clearComparison } =
    useComparison();
  const [showOnlyDifferences, setShowOnlyDifferences] = useState(false);

  if (comparisonList.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-3xl font-bold mb-8">{t.ui.comparison}</h1>
          <p className="mb-8 text-gray-600">{t.ui.no_bikes_to_compare}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            ← {t.ui.back_to_search}
          </Link>
        </div>
      </div>
    );
  }

  const geometryKeys: (keyof Geometry)[] = [
    "stack",
    "reach",
    "top_tube_effective_length",
    "seat_tube_length",
    "head_tube_length",
    "chainstay_length",
    "head_tube_angle",
    "seat_tube_angle",
    "bb_drop",
    "wheelbase",
  ];

  const isDifferent = (key: keyof Geometry) => {
    if (comparisonList.length < 2) return false;
    const firstValue = comparisonList[0].geometry[key];
    return comparisonList.some((item) => item.geometry[key] !== firstValue);
  };

  const filteredKeys = showOnlyDifferences
    ? geometryKeys.filter(isDifferent)
    : geometryKeys;

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex justify-between items-center mb-8">
          <Link href="/" className="text-blue-600 hover:underline">
            ← {t.ui.back_to_search}
          </Link>
          <div className="flex items-center gap-4">
            <LanguageSwitcher />
            <button
              onClick={clearComparison}
              className="text-red-600 hover:underline text-sm font-medium"
            >
              {t.ui.clear_comparison}
            </button>
          </div>
        </div>

        <div className="flex justify-between items-end mb-6">
          <h1 className="text-4xl font-extrabold text-gray-900">
            {t.ui.comparison} ({comparisonList.length})
          </h1>
          <label className="flex items-center gap-2 cursor-pointer bg-white px-4 py-2 rounded-lg border border-gray-200 shadow-sm">
            <input
              type="checkbox"
              checked={showOnlyDifferences}
              onChange={(e) => setShowOnlyDifferences(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm font-medium text-gray-700">
              {t.ui.show_only_differences}
            </span>
          </label>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500 uppercase text-xs font-semibold border-b">
                  <th className="py-4 px-6 border-r sticky left-0 bg-gray-50 z-10 w-48">
                    {t.ui.metadata}
                  </th>
                  {comparisonList.map((item, idx) => (
                    <th key={idx} className="py-4 px-6 min-w-[200px] border-r">
                      <div className="flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="text-gray-900 font-bold normal-case text-base">
                              {item.bike.brand} {item.bike.model_name}
                            </p>
                            <p className="text-gray-500 font-medium normal-case">
                              {t.geometry.size_label}:{" "}
                              {item.geometry.size_label}
                            </p>
                          </div>
                          <button
                            onClick={() =>
                              removeFromCompare(
                                item.bike.id,
                                item.geometry.size_label,
                              )
                            }
                            className="text-red-400 hover:text-red-600 p-1"
                          >
                            ✕
                          </button>
                        </div>
                        <div className="bg-gray-50 rounded p-2 flex justify-center">
                          <BikeFrameSVG geometry={item.geometry} height={70} />
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {/* Basic Info */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                    {t.ui.year}
                  </td>
                  {comparisonList.map((item, idx) => (
                    <td key={idx} className="py-3 px-6 border-r">
                      {item.bike.model_year || "-"}
                    </td>
                  ))}
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                    {t.ui.material}
                  </td>
                  {comparisonList.map((item, idx) => (
                    <td key={idx} className="py-3 px-6 border-r text-xs">
                      {item.bike.frame_material || "-"}
                    </td>
                  ))}
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                    {t.ui.wheel_size}
                  </td>
                  {comparisonList.map((item, idx) => (
                    <td key={idx} className="py-3 px-6 border-r text-xs">
                      {item.bike.wheel_size
                        ? t.wheel_sizes[item.bike.wheel_size] ||
                          item.bike.wheel_size
                        : "-"}
                    </td>
                  ))}
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                    {t.ui.source_page}
                  </td>
                  {comparisonList.map((item, idx) => (
                    <td key={idx} className="py-3 px-6 border-r text-xs">
                      {item.bike.source_url ? (
                        <a
                          href={item.bike.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {t.ui.source_page} ↗
                        </a>
                      ) : (
                        "-"
                      )}
                    </td>
                  ))}
                </tr>

                {/* Geometry Params */}
                {filteredKeys.map((key) => (
                  <tr key={key} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 px-6 font-medium text-gray-900 bg-gray-50/50 border-r sticky left-0 z-10">
                      {t.geometry[key as keyof typeof t.geometry]}
                    </td>
                    {comparisonList.map((item, idx) => (
                      <td
                        key={idx}
                        className={`py-3 px-6 border-r font-mono ${
                          isDifferent(key)
                            ? "text-blue-600 font-bold"
                            : "text-gray-700"
                        }`}
                      >
                        {item.geometry[key]}
                        {key.includes("angle") ? "°" : " mm"}
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
