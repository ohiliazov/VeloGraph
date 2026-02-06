"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import BikeFrameSVG from "./BikeFrameSVG";
import {
  BikeGroup,
  BikeProduct,
  SearchResult,
  GroupedSearchResult,
  BikeCategory,
  MaterialGroup,
} from "@/types";
import { useLanguage } from "@/context/LanguageContext";
import { useComparison } from "@/context/ComparisonContext";

export default function BikeSearch() {
  const { t } = useLanguage();
  const { addToCompare, removeFromCompare, isInComparison, comparisonList } =
    useComparison();
  const [stack, setStack] = useState("");
  const [reach, setReach] = useState("");
  const [category, setCategory] = useState("");
  const [material, setMaterial] = useState("");
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"geometry" | "keyword">(
    "geometry",
  );
  const [results, setResults] = useState<BikeProduct[] | BikeGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState<
    Record<string, number>
  >({});

  const canSearch =
    activeTab === "geometry"
      ? Boolean(stack && reach)
      : Boolean(query.trim() || category || material);

  const searchBikes = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();

      if (category) params.append("category", category);
      if (material) params.append("material", material);

      // Pagination first to ensure it's included in the URL below
      params.append("page", page.toString());
      params.append("size", "10");

      let url = "";
      if (activeTab === "geometry") {
        if (stack) params.append("stack", stack);
        if (reach) params.append("reach", reach);
        url = `http://localhost:8000/api/bikes/search/geometry?${params.toString()}`;
      } else {
        if (query.trim()) params.append("q", query.trim());
        url = `http://localhost:8000/api/bikes/search/keyword?${params.toString()}`;
      }

      if (!canSearch) {
        setResults([]);
        setTotal(0);
        return;
      }

      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Search failed with status: ${res.status}`);
      }

      if (activeTab === "geometry") {
        const data = (await res.json()) as SearchResult;
        setResults(data.items || []);
        setTotal(data.total || 0);
      } else {
        const data = (await res.json()) as GroupedSearchResult;
        setResults(data.items || []);
        setTotal(data.total || 0);

        // Initialize size selection for groups
        const initialSelection: Record<string, number> = {};
        data.items?.forEach((group) => {
          const groupKey = `${group.frameset_name}-${group.build_kit.id}`;
          if (group.products.length > 0) {
            initialSelection[groupKey] = group.products[0].id;
          }
        });
        setSelectedProductIds((prev) => ({ ...prev, ...initialSelection }));
      }
    } catch (err) {
      console.error("Failed to fetch bikes:", err);
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [category, reach, stack, query, page, material, canSearch, activeTab]);

  useEffect(() => {
    // Only fetch if search criteria are met
    if (canSearch) {
      searchBikes();
    } else {
      setResults([]);
      setTotal(0);
    }
  }, [searchBikes, canSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    searchBikes();
  };

  return (
    <div className="w-full max-w-5xl mx-auto p-4 md:p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-4 rounded-2xl border border-gray-200 shadow-sm sticky top-4 z-30">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 leading-tight">
              Bike Search
            </h1>
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">
              {total} {t.ui.results_found}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Link
            href="/bikes/new"
            className="flex-1 md:flex-none bg-orange-600 text-white px-5 py-2.5 rounded-xl font-semibold hover:bg-orange-700 transition-all shadow-sm hover:shadow-md active:scale-95 flex items-center justify-center gap-2 text-sm"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            {t.ui.create_bike}
          </Link>
          {comparisonList.length > 0 && (
            <Link
              href="/compare"
              className="flex-1 md:flex-none bg-green-600 text-white px-5 py-2.5 rounded-xl font-semibold hover:bg-green-700 transition-all shadow-sm hover:shadow-md active:scale-95 flex items-center justify-center gap-2 text-sm animate-in fade-in slide-in-from-right-4 duration-300"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              {t.ui.compare} ({comparisonList.length})
            </Link>
          )}
        </div>
      </div>

      <div className="flex p-1 bg-gray-100 rounded-2xl w-fit mx-auto md:mx-0">
        <button
          type="button"
          onClick={() => {
            setActiveTab("geometry");
            setPage(1);
          }}
          className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${
            activeTab === "geometry"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t.ui.geometry_tab}
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab("keyword");
            setPage(1);
          }}
          className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${
            activeTab === "keyword"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t.ui.keyword_tab}
        </button>
      </div>

      <form
        onSubmit={handleSearch}
        className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-white p-5 rounded-2xl border border-gray-200 shadow-sm"
      >
        {activeTab === "keyword" && (
          <div className="col-span-2 space-y-1.5">
            <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
              {t.ui.brand} / {t.ui.model}
            </label>
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t.ui.search_placeholder}
                className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-sm transition-all"
              />
              <svg
                className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </div>
        )}
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
            {t.ui.category}
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-sm transition-all appearance-none cursor-pointer"
          >
            <option value="">{t.categories.all_categories}</option>
            {Object.values(BikeCategory).map((value) => (
              <option key={value} value={value}>
                {t.categories[value as keyof typeof t.categories]}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
            {t.ui.material}
          </label>
          <select
            value={material}
            onChange={(e) => setMaterial(e.target.value)}
            className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-sm transition-all appearance-none cursor-pointer"
          >
            <option value="">{t.ui.all_materials}</option>
            {Object.values(MaterialGroup).map((value) => (
              <option key={value} value={value}>
                {t.ui[value as keyof typeof t.ui] || value}
              </option>
            ))}
          </select>
        </div>

        {activeTab === "geometry" && (
          <>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
                {t.ui.stack_target}
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={stack}
                  onChange={(e) => setStack(e.target.value)}
                  placeholder="e.g. 580"
                  className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-sm transition-all"
                  required
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-gray-400 uppercase">
                  mm
                </span>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
                {t.ui.reach_target}
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={reach}
                  onChange={(e) => setReach(e.target.value)}
                  placeholder="e.g. 400"
                  className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-sm transition-all"
                  required
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-gray-400 uppercase">
                  mm
                </span>
              </div>
            </div>
          </>
        )}
      </form>

      {total > 10 && (
        <div className="flex justify-center items-center gap-4 bg-white py-2 px-4 rounded-xl border border-gray-200 shadow-sm w-fit mx-auto">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-30 disabled:hover:bg-transparent transition-all"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              Page
            </span>
            <span className="text-sm font-bold text-blue-600">{page}</span>
          </div>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={results.length < 10}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-30 disabled:hover:bg-transparent transition-all"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-10">{t.ui.loading}</div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 table-fixed">
              <thead className="bg-gray-50/50">
                <tr>
                  <th className="w-[32%] px-6 py-4 text-left text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    {t.ui.brand} / {t.ui.model}
                  </th>
                  <th className="w-[12%] px-4 py-4 text-center text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    {t.geometry.size_label}
                  </th>
                  <th className="w-[16%] px-4 py-4 text-left text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    Geometry (S/R)
                  </th>
                  {activeTab === "geometry" && (
                    <th className="w-[25%] px-6 py-4 text-center text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                      Target Fit
                    </th>
                  )}
                  <th className="w-[15%] px-6 py-4 text-right text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    {t.ui.actions || "Actions"}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {results.map((item) => {
                  const isGroup = "products" in item;
                  const groupKey = isGroup
                    ? `${item.frameset_name}-${item.build_kit.id}`
                    : "";
                  const selectedId = isGroup
                    ? selectedProductIds[groupKey] || item.products[0]?.id
                    : (item as BikeProduct).id;
                  const product = isGroup
                    ? item.products.find((p) => p.id === selectedId) ||
                      item.products[0]
                    : (item as BikeProduct);

                  if (!product) return null;

                  const isProductInComparison = isInComparison(product.id);
                  const sDiff = product.frameset.stack - Number(stack);
                  const rDiff = product.frameset.reach - Number(reach);

                  // Visualization range based on average size differences
                  const RANGE = 20;
                  const getPosition = (diff: number) => {
                    const percent = ((diff + RANGE) / (RANGE * 2)) * 100;
                    return Math.min(Math.max(percent, 0), 100);
                  };

                  const getFitColor = (diff: number) => {
                    const absDiff = Math.abs(diff);
                    if (absDiff <= 2) return "text-purple-600";
                    if (absDiff <= 5) return "text-blue-600";
                    if (absDiff <= 10) return "text-green-600";
                    if (absDiff <= 18) return "text-amber-600";
                    return "text-red-600";
                  };

                  const getFitLabel = (diff: number) => {
                    const absDiff = Math.abs(diff);
                    if (absDiff <= 2) return t.fit.ideal;
                    if (absDiff <= 5) return t.fit.excellent;
                    if (absDiff <= 10) return t.fit.good;
                    if (absDiff <= 18) return t.fit.average;
                    return t.fit.poor;
                  };

                  return (
                    <tr
                      key={isGroup ? groupKey : product.id}
                      className="group hover:bg-blue-50/40 transition-all duration-200"
                    >
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className="flex-shrink-0 h-14 w-20 bg-gray-50 rounded-xl flex items-center justify-center p-2 group-hover:bg-white transition-all border border-gray-100 group-hover:border-blue-100 group-hover:shadow-sm">
                            <BikeFrameSVG
                              geometry={product.frameset}
                              height={44}
                            />
                          </div>
                          <div className="min-w-0 flex-1">
                            <Link
                              href={`/bikes/${product.id}`}
                              className="text-sm font-bold text-gray-900 hover:text-blue-600 transition-colors block truncate"
                            >
                              {product.frameset.name}
                            </Link>
                            <div className="flex flex-wrap items-center gap-2 mt-1.5">
                              <span className="text-[10px] font-extrabold text-blue-500 bg-blue-50/50 px-2 py-0.5 rounded-md uppercase tracking-wider border border-blue-100/50">
                                {product.frameset.material || "N/A"}
                              </span>
                              <span className="text-[10px] font-medium text-gray-400 truncate max-w-[120px]">
                                {product.build_kit.name}
                              </span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        {isGroup ? (
                          <div className="flex flex-wrap justify-center gap-1.5">
                            {(item as BikeGroup).products.map((p) => (
                              <button
                                key={p.id}
                                onClick={() =>
                                  setSelectedProductIds((prev) => ({
                                    ...prev,
                                    [groupKey]: p.id,
                                  }))
                                }
                                className={`min-w-[32px] px-1.5 py-0.5 text-[10px] font-bold rounded-md transition-all ${
                                  selectedId === p.id
                                    ? "bg-blue-600 text-white shadow-sm ring-2 ring-blue-600/20 scale-105"
                                    : "bg-gray-50 text-gray-500 hover:bg-gray-200 hover:text-gray-700 border border-gray-200"
                                }`}
                              >
                                {p.frameset.size_label}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <span className="inline-flex items-center justify-center min-w-[32px] px-2 py-1 text-[11px] font-black rounded-lg bg-gray-900 text-white shadow-sm">
                            {product.frameset.size_label}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-5 whitespace-nowrap">
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center gap-2">
                            <span className="w-3 text-[10px] font-black text-gray-300">
                              S
                            </span>
                            <span className="text-sm font-bold text-gray-800 tabular-nums">
                              {product.frameset.stack}
                            </span>
                            <span className="text-[10px] text-gray-400 font-medium">
                              mm
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-3 text-[10px] font-black text-gray-300">
                              R
                            </span>
                            <span className="text-sm font-bold text-gray-800 tabular-nums">
                              {product.frameset.reach}
                            </span>
                            <span className="text-[10px] text-gray-400 font-medium">
                              mm
                            </span>
                          </div>
                        </div>
                      </td>
                      {activeTab === "geometry" && (
                        <td className="px-6 py-5">
                          {canSearch && (
                            <div className="flex flex-col gap-4 max-w-[180px] mx-auto">
                              {/* Stack Fit */}
                              <div className="space-y-1.5">
                                <div className="flex items-end justify-between relative h-4">
                                  <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">
                                    Stack
                                  </span>
                                  <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center">
                                    <span
                                      className={`text-[11px] font-bold tabular-nums leading-none ${getFitColor(
                                        sDiff,
                                      )}`}
                                    >
                                      {sDiff > 0 ? "+" : ""}
                                      {sDiff.toFixed(1)}
                                    </span>
                                    <span className="text-[7px] text-gray-400 font-bold uppercase">
                                      mm
                                    </span>
                                  </div>
                                  <span
                                    className={`text-[9px] font-black uppercase tracking-wider ${getFitColor(
                                      sDiff,
                                    )}`}
                                  >
                                    {getFitLabel(sDiff)}
                                  </span>
                                </div>
                                <div className="relative py-1">
                                  <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden border border-gray-200/50 shadow-inner">
                                    <div
                                      className="absolute inset-0"
                                      style={{
                                        background:
                                          "linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #22c55e 37.5%, #3b82f6 45%, #a855f7 50%, #3b82f6 55%, #22c55e 62.5%, #f59e0b 75%, #ef4444 100%)",
                                      }}
                                    />
                                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/40 z-10" />
                                  </div>
                                  <div
                                    className="absolute top-1/2 w-0.5 h-4 bg-gray-950 z-20 transition-all duration-700 ease-out rounded-full shadow-[0_0_2px_rgba(255,255,255,0.8)]"
                                    style={{
                                      left: `${getPosition(sDiff)}%`,
                                      transform: "translate(-50%, -50%)",
                                    }}
                                  />
                                </div>
                                <div className="flex justify-between px-0.5">
                                  <span className="text-[8px] font-bold text-gray-300 tracking-tighter">
                                    -20
                                  </span>
                                  <span className="text-[8px] font-bold text-gray-400">
                                    0
                                  </span>
                                  <span className="text-[8px] font-bold text-gray-300 tracking-tighter">
                                    +20
                                  </span>
                                </div>
                              </div>
                              {/* Reach Fit */}
                              <div className="space-y-1.5">
                                <div className="flex items-end justify-between relative h-4">
                                  <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">
                                    Reach
                                  </span>
                                  <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center">
                                    <span
                                      className={`text-[11px] font-bold tabular-nums leading-none ${getFitColor(
                                        rDiff,
                                      )}`}
                                    >
                                      {rDiff > 0 ? "+" : ""}
                                      {rDiff.toFixed(1)}
                                    </span>
                                    <span className="text-[7px] text-gray-400 font-bold uppercase">
                                      mm
                                    </span>
                                  </div>
                                  <span
                                    className={`text-[9px] font-black uppercase tracking-wider ${getFitColor(
                                      rDiff,
                                    )}`}
                                  >
                                    {getFitLabel(rDiff)}
                                  </span>
                                </div>
                                <div className="relative py-1">
                                  <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden border border-gray-200/50 shadow-inner">
                                    <div
                                      className="absolute inset-0"
                                      style={{
                                        background:
                                          "linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #22c55e 37.5%, #3b82f6 45%, #a855f7 50%, #3b82f6 55%, #22c55e 62.5%, #f59e0b 75%, #ef4444 100%)",
                                      }}
                                    />
                                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/40 z-10" />
                                  </div>
                                  <div
                                    className="absolute top-1/2 w-0.5 h-4 bg-gray-950 z-20 transition-all duration-700 ease-out rounded-full shadow-[0_0_2px_rgba(255,255,255,0.8)]"
                                    style={{
                                      left: `${getPosition(rDiff)}%`,
                                      transform: "translate(-50%, -50%)",
                                    }}
                                  />
                                </div>
                                <div className="flex justify-between px-0.5">
                                  <span className="text-[8px] font-bold text-gray-300 tracking-tighter">
                                    -20
                                  </span>
                                  <span className="text-[8px] font-bold text-gray-400">
                                    0
                                  </span>
                                  <span className="text-[8px] font-bold text-gray-300 tracking-tighter">
                                    +20
                                  </span>
                                </div>
                              </div>
                            </div>
                          )}
                        </td>
                      )}
                      <td className="px-6 py-5 text-right">
                        <div className="flex justify-end items-center gap-2">
                          <button
                            onClick={() =>
                              isProductInComparison
                                ? removeFromCompare(product.id)
                                : addToCompare(product)
                            }
                            className={`flex items-center justify-center w-9 h-9 rounded-xl transition-all ${
                              isProductInComparison
                                ? "bg-red-50 text-red-600 hover:bg-red-100 shadow-inner"
                                : "bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white hover:shadow-lg hover:-translate-y-0.5"
                            }`}
                            title={
                              isProductInComparison
                                ? t.ui.remove_from_compare
                                : t.ui.add_to_compare
                            }
                          >
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2.5"
                                d={
                                  isProductInComparison
                                    ? "M20 12H4"
                                    : "M12 4v16m8-8H4"
                                }
                              />
                            </svg>
                          </button>

                          <Link
                            href={`/bikes/${product.id}`}
                            className="flex items-center justify-center w-9 h-9 bg-gray-50 text-gray-400 rounded-xl hover:bg-white hover:text-gray-900 transition-all border border-transparent hover:border-gray-200 hover:shadow-sm"
                            title="View Details"
                          >
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2.5"
                                d="M9 5l7 7-7 7"
                              />
                            </svg>
                          </Link>

                          {product.source_url && (
                            <a
                              href={product.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center justify-center w-9 h-9 bg-gray-50 text-gray-400 rounded-xl hover:bg-white hover:text-blue-600 transition-all border border-transparent hover:border-gray-200 hover:shadow-sm"
                              title={t.ui.source_page}
                            >
                              <svg
                                className="w-5 h-5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 text-gray-300">
              <svg
                className="w-16 h-16 mb-4 opacity-20"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1"
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                />
              </svg>
              <p className="text-sm font-medium">{t.ui.no_results}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
