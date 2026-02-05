"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import BikeFrameSVG from "./BikeFrameSVG";
import { BikeGroup, BikeProduct, SearchResult } from "@/types";
import { useLanguage } from "@/context/LanguageContext";
import { useComparison } from "@/context/ComparisonContext";

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
  const [results, setResults] = useState<BikeGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState<
    Record<string, number>
  >({});

  const searchBikes = useCallback(async () => {
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

      let groups: BikeGroup[] = [];
      if (isSearching) {
        groups = (data as SearchResult).items;
      } else {
        groups = data as BikeGroup[];
      }
      setResults(groups);

      // Initialize selected products (default to first available size)
      const initialSelection: Record<string, number> = {};
      groups.forEach((group) => {
        const groupKey = `${group.frameset_name}-${group.build_kit.id}`;
        if (group.products.length > 0) {
          initialSelection[groupKey] = group.products[0].id;
        }
      });
      setSelectedProductIds(initialSelection);
    } catch (err) {
      console.error("Failed to fetch bikes:", err);
    } finally {
      setLoading(false);
    }
  }, [category, query, reachMax, reachMin, stackMax, stackMin]);

  useEffect(() => {
    searchBikes();
  }, [searchBikes]);

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
        <div className="flex gap-2 bg-white p-2 rounded-xl border border-gray-200 shadow-sm sticky top-4 z-20 backdrop-blur-md bg-white/90">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.ui.search_placeholder}
            className="flex-1 p-2 border border-gray-300 rounded-lg shadow-inner focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md active:scale-95"
          >
            {t.ui.search_button}
          </button>
          <Link
            href="/bikes/new"
            className="bg-orange-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-orange-700 transition-all shadow-md active:scale-95 flex items-center gap-2"
          >
            {t.ui.create_bike}
          </Link>
          {comparisonList.length > 0 && (
            <Link
              href="/compare"
              className="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition-all shadow-md active:scale-95 flex items-center gap-2 animate-in fade-in zoom-in duration-300"
            >
              {t.ui.compare} ({comparisonList.length})
            </Link>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
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
          {results.map((group) => {
            const groupKey = `${group.frameset_name}-${group.build_kit.id}`;
            const selectedProductId = selectedProductIds[groupKey];
            const selectedProduct =
              group.products.find((p) => p.id === selectedProductId) ||
              group.products[0];

            if (!selectedProduct) return null;

            return (
              <div
                key={groupKey}
                className="border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow bg-white"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-gray-900">
                      <Link
                        href={`/bikes/${selectedProduct.id}`}
                        className="hover:text-blue-600"
                      >
                        {group.frameset_name}
                      </Link>
                    </h2>
                    <p className="text-sm text-gray-500">
                      {group.material && (
                        <span className="text-xs text-gray-400">
                          {group.material}
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="mb-4 bg-gray-50 rounded-lg flex justify-center p-2">
                  <BikeFrameSVG
                    geometry={selectedProduct.frameset}
                    height={100}
                    className="max-w-full"
                  />
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between items-center border-b pb-1">
                    <h3 className="text-sm font-semibold text-gray-700">
                      {t.ui.geometries}
                    </h3>
                    <div className="text-xs text-gray-500">
                      {group.build_kit.name}
                    </div>
                  </div>

                  <div className="overflow-x-auto -mx-6 px-6">
                    <table className="min-w-full text-xs text-left">
                      <thead>
                        <tr className="text-gray-400 uppercase tracking-tighter border-b border-gray-100">
                          <th className="py-2 pr-2 font-bold">
                            {t.geometry.size_label}
                          </th>
                          <th className="py-2 px-2">{t.geometry.stack}</th>
                          <th className="py-2 px-2">{t.geometry.reach}</th>
                          <th className="py-2 px-2">HA</th>
                          <th className="py-2 px-2">SA</th>
                          <th className="py-2 pl-2 text-right"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {group.products.map((p) => {
                          const g = p.frameset;
                          const inCompare = isInComparison(p.id);
                          const isSelected = selectedProduct.id === p.id;
                          return (
                            <tr
                              key={p.id}
                              className={`text-gray-700 hover:bg-gray-50 cursor-pointer transition-colors ${
                                isSelected ? "bg-blue-50/50" : ""
                              }`}
                              onClick={() =>
                                setSelectedProductIds((prev) => ({
                                  ...prev,
                                  [groupKey]: p.id,
                                }))
                              }
                            >
                              <td className="py-2 pr-2 font-medium">
                                {g.size_label}
                              </td>
                              <td className="py-2 px-2">{g.stack}</td>
                              <td className="py-2 px-2">{g.reach}</td>
                              <td className="py-2 px-2">
                                {g.head_tube_angle}°
                              </td>
                              <td className="py-2 px-2">
                                {g.seat_tube_angle}°
                              </td>
                              <td className="py-2 pl-2 text-right">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    inCompare
                                      ? removeFromCompare(p.id)
                                      : addToCompare(p);
                                  }}
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
            );
          })}
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
