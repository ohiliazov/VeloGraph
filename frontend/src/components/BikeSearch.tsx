"use client";

import { useState, useEffect } from "react";
import { Bike, SearchResult } from "../types";

export default function BikeSearch() {
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
            placeholder="Search bikes (e.g. Kross Esker)..."
            className="flex-1 p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            Search
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              Stack Min
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
              Stack Max
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
              Reach Min
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
              Reach Max
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
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-sm bg-white"
            >
              <option value="">All Categories</option>
              <option value="gravel">Gravel</option>
              <option value="mtb">MTB</option>
              <option value="road">Road</option>
              <option value="trekking">Trekking</option>
              <option value="cross">Cross</option>
              <option value="city">City</option>
              <option value="kids">Kids</option>
              <option value="touring">Touring</option>
              <option value="women">Women</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      </form>

      {loading ? (
        <div className="text-center py-10">Loading bikes...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {results.map((bike) => (
            <div
              key={bike.id}
              className="border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow bg-white"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {bike.brand} {bike.model_name}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {bike.categories.join(" / ")}
                  </p>
                </div>
                {bike.model_year && (
                  <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-semibold">
                    {bike.model_year}
                  </span>
                )}
              </div>

              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 border-b pb-1">
                  Geometries
                </h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs text-left">
                    <thead>
                      <tr className="text-gray-400">
                        <th className="py-1 pr-2">Size</th>
                        <th className="py-1 px-2">Stack</th>
                        <th className="py-1 px-2">Reach</th>
                        <th className="py-1 px-2">HA</th>
                        <th className="py-1 px-2">SA</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {bike.geometries.map((g) => (
                        <tr key={g.size_label} className="text-gray-700">
                          <td className="py-2 pr-2 font-medium">
                            {g.size_label}
                          </td>
                          <td className="py-2 px-2">{g.stack}</td>
                          <td className="py-2 px-2">{g.reach}</td>
                          <td className="py-2 px-2">{g.head_tube_angle}°</td>
                          <td className="py-2 px-2">{g.seat_tube_angle}°</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ))}
          {results.length === 0 && (
            <div className="col-span-full text-center py-20 text-gray-500">
              No bikes found. Try a different search term.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
