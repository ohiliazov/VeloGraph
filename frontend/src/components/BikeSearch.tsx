"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import BikeFrameSVG from "./BikeFrameSVG";
import { Bike, SearchResult } from "../types";
import { useLanguage } from "../context/LanguageContext";
import { useComparison } from "../context/ComparisonContext";
import { translations } from "../translations";

export default function BikeSearch() {
  const { t } = useLanguage();
  const { addToCompare, removeFromCompare, isInComparison, comparisonList } =
    useComparison();
  const [query, setQuery] = useState("");
  const [stackMin, setStackMin] = useState("");
  const [stackMax, setStackMax] = useState("");
  const [reachMin, setReachMin] = useState("");
  const [reachMax, setReachMax] = useState("");
  const [category, setCategory] = useState("");
  const [results, setResults] = useState<Bike[]>([]);
  const [loading, setLoading] = useState(false);

  const searchBikes = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.append("q", query);
      if (stackMin) params.append("stack_min", stackMin);
      if (stackMax) params.append("stack_max", stackMax);
      if (reachMin) params.append("reach_min", reachMin);
      if (reachMax) params.append("reach_max", reachMax);
      if (category) params.append("category", category);

      const isSearching = params.toString().length > 0;
      const url = isSearching
        ? `http://localhost:8000/api/bikes/search?${params.toString()}`
        : `http://localhost:8000/api/bikes/`;

      const res = await fetch(url);
      const data = await res.json();

      if (isSearching) {
        setResults((data as SearchResult).items);
      } else {
        setResults(data as Bike[]);
      }
    } catch (err) {
      console.error("Failed to fetch bikes:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    searchBikes();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchBikes();
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      <form
        onSubmit={handleSearch}
        className="mb-8 space-y-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.ui.search_placeholder}
            className="flex-1 p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            {t.ui.search_button}
          </button>
          {comparisonList.length > 0 && (
            <Link
              href="/compare"
              className="bg-green-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-700 transition-colors shadow-sm flex items-center gap-2"
            >
              {t.ui.compare} ({comparisonList.length})
            </Link>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              {t.ui.stack_min}
            </label>
            <input
              type="number"
              value={stackMin}
              onChange={(e) => setStackMin(e.target.value)}
              placeholder="e.g. 500"
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              {t.ui.stack_max}
            </label>
            <input
              type="number"
              value={stackMax}
              onChange={(e) => setStackMax(e.target.value)}
              placeholder="e.g. 650"
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              {t.ui.reach_min}
            </label>
            <input
              type="number"
              value={reachMin}
              onChange={(e) => setReachMin(e.target.value)}
              placeholder="e.g. 350"
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              {t.ui.reach_max}
            </label>
            <input
              type="number"
              value={reachMax}
              onChange={(e) => setReachMax(e.target.value)}
              placeholder="e.g. 450"
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              {t.ui.category}
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm bg-white"
            >
              <option value="">{t.categories.all_categories}</option>
              {Object.entries(t.categories)
                .filter(([key]) => key !== "all_categories")
                .map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </form>

      {loading ? (
        <div className="text-center py-10">{t.ui.loading}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {results.map((bike) => (
            <div
              key={bike.id}
              className="border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow bg-white"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-gray-900">
                    <Link
                      href={`/bikes/${bike.id}`}
                      className="hover:text-blue-600"
                    >
                      {bike.brand} {bike.model_name}
                    </Link>
                  </h2>
                  <p className="text-sm text-gray-500">
                    {bike.categories
                      .map(
                        (c) =>
                          t.categories[c as keyof typeof t.categories] || c,
                      )
                      .join(" / ")}
                    {bike.wheel_size && (
                      <span className="ml-2 text-xs text-gray-400">
                        • {t.wheel_sizes[bike.wheel_size] || bike.wheel_size}
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  {bike.model_year && (
                    <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-semibold">
                      {bike.model_year}
                    </span>
                  )}
                  <Link
                    href={`/bikes/${bike.id}/edit`}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {t.ui.edit}
                  </Link>
                </div>
              </div>

              {bike.geometries.length > 0 && (
                <div className="mb-4 bg-gray-50 rounded-lg flex justify-center p-2">
                  <BikeFrameSVG
                    geometry={bike.geometries[0]}
                    height={100}
                    className="max-w-full"
                  />
                </div>
              )}

              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 border-b pb-1">
                  {t.ui.geometries}
                </h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs text-left">
                    <thead>
                      <tr className="text-gray-400">
                        <th className="py-1 pr-2">{t.geometry.size_label}</th>
                        <th className="py-1 px-2">{t.geometry.stack}</th>
                        <th className="py-1 px-2">{t.geometry.reach}</th>
                        <th className="py-1 px-2">
                          {t.geometry.head_tube_angle} (HA)
                        </th>
                        <th className="py-1 px-2">
                          {t.geometry.seat_tube_angle} (SA)
                        </th>
                        <th className="py-1 pl-2 text-right"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {bike.geometries.map((g) => {
                        const inCompare = isInComparison(bike.id, g.size_label);
                        return (
                          <tr key={g.size_label} className="text-gray-700">
                            <td className="py-2 pr-2 font-medium">
                              {g.size_label}
                            </td>
                            <td className="py-2 px-2">{g.stack}</td>
                            <td className="py-2 px-2">{g.reach}</td>
                            <td className="py-2 px-2">{g.head_tube_angle}°</td>
                            <td className="py-2 px-2">{g.seat_tube_angle}°</td>
                            <td className="py-2 pl-2 text-right">
                              <button
                                onClick={() =>
                                  inCompare
                                    ? removeFromCompare(bike.id, g.size_label)
                                    : addToCompare(bike, g)
                                }
                                className={`text-[10px] px-2 py-1 rounded transition-colors ${
                                  inCompare
                                    ? "bg-red-100 text-red-600 hover:bg-red-200"
                                    : "bg-blue-50 text-blue-600 hover:bg-blue-100"
                                }`}
                              >
                                {inCompare
                                  ? t.ui.remove_from_compare
                                  : t.ui.add_to_compare}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ))}
          {results.length === 0 && (
            <div className="col-span-full text-center py-20 text-gray-500">
              {t.ui.no_results}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
