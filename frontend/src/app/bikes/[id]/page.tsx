"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import BikeFrameSVG from "../../../components/BikeFrameSVG";
import { Bike } from "../../../types";
import { useLanguage } from "../../../context/LanguageContext";
import { useComparison } from "../../../context/ComparisonContext";
import LanguageSwitcher from "../../../components/LanguageSwitcher";

export default function BikeDetailPage() {
  const { id } = useParams();
  const { t } = useLanguage();
  const { addToCompare, removeFromCompare, isInComparison, comparisonList } =
    useComparison();
  const [bike, setBike] = useState<Bike | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBike = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/bikes/${id}`);
        if (!res.ok) throw new Error("Failed to fetch bike details");
        const data = await res.json();
        setBike(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchBike();
  }, [id]);

  if (loading) return <div className="text-center py-20">{t.ui.loading}</div>;
  if (error)
    return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!bike)
    return (
      <div className="text-center py-20">{t.categories.bike_not_found}</div>
    );

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex justify-between items-center mb-8">
          <Link href="/" className="text-blue-600 hover:underline">
            ← {t.ui.back_to_search}
          </Link>
          <div className="flex items-center gap-4">
            <LanguageSwitcher />
            {comparisonList.length > 0 && (
              <Link
                href="/compare"
                className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors shadow-sm"
              >
                {t.ui.compare} ({comparisonList.length})
              </Link>
            )}
            <Link
              href={`/bikes/${id}/edit`}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
            >
              {t.ui.edit_bike}
            </Link>
            {bike.source_url && (
              <a
                href={bike.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-gray-800 text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-900 transition-colors shadow-sm inline-flex items-center gap-2"
              >
                {t.ui.source_page} ↗
              </a>
            )}
          </div>
        </div>

        <header className="mb-8">
          <h1 className="text-4xl font-extrabold text-gray-900">
            {bike.brand} {bike.model_name}
          </h1>
          <p className="text-xl text-gray-500 mt-2">
            {bike.categories
              .map((c) => t.categories[c as keyof typeof t.categories] || c)
              .join(" / ")}{" "}
            {bike.model_year ? `(${bike.model_year})` : ""}
          </p>
        </header>

        <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm mb-12 flex justify-center">
          <BikeFrameSVG
            geometry={bike.geometries[0]}
            wheelSize={bike.wheel_size}
            maxTireWidth={bike.max_tire_width}
            frameColor={bike.color}
            height={200}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.brand}
            </h3>
            <p className="text-lg font-medium text-gray-900">{bike.brand}</p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.model}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.model_name}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.year}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.model_year || "N/A"}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.material}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.frame_material || "N/A"}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.wheel_size}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.wheel_size
                ? t.wheel_sizes[bike.wheel_size] || bike.wheel_size
                : "N/A"}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.brake_type}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.brake_type || "N/A"}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.ui.max_tire_width}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.max_tire_width ? `${bike.max_tire_width} mm` : "N/A"}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {t.geometry.colors}
            </h3>
            <p className="text-lg font-medium text-gray-900">
              {bike.color || "N/A"}
            </p>
          </div>
          {bike.source_url && (
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                {t.ui.source_page}
              </h3>
              <a
                href={bike.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lg font-medium text-blue-600 hover:underline inline-flex items-center gap-1"
              >
                {t.ui.source_page} ↗
              </a>
            </div>
          )}
        </div>

        <section className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-xl font-bold text-gray-900">
              {t.ui.geometry_details}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500 uppercase text-xs font-semibold border-b">
                  <th className="py-4 px-6 border-r sticky left-0 bg-gray-50 z-10 w-48">
                    {t.ui.geometry_details}
                  </th>
                  {bike.geometries.map((geo, index) => (
                    <th
                      key={`${bike.id}-${geo.size_label}-${index}`}
                      className="py-4 px-6 text-center border-r min-w-[120px]"
                    >
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-base font-bold text-gray-900 normal-case">
                          {geo.size_label}
                        </span>
                        <div className="bg-gray-100 rounded p-1 flex justify-center">
                          <BikeFrameSVG
                            geometry={geo}
                            wheelSize={bike.wheel_size}
                            maxTireWidth={bike.max_tire_width}
                            height={40}
                          />
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(
                  [
                    "stack",
                    "reach",
                    "top_tube_effective_length",
                    "seat_tube_length",
                    "head_tube_angle",
                    "seat_tube_angle",
                    "wheelbase",
                  ] as (keyof typeof t.geometry)[]
                ).map((key) => (
                  <tr key={key} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                      {t.geometry[key]}
                    </td>
                    {bike.geometries.map((geo, index) => (
                      <td
                        key={`${bike.id}-${geo.size_label}-${index}-${key}`}
                        className="py-3 px-6 text-center border-r font-mono text-gray-700"
                      >
                        {geo[key as keyof typeof geo]}
                        {String(key).includes("angle") ? "°" : " mm"}
                      </td>
                    ))}
                  </tr>
                ))}
                {/* Comparison Actions Row */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="py-4 px-6 font-medium text-gray-500 bg-gray-50/30 border-r sticky left-0 z-10">
                    {t.ui.compare}
                  </td>
                  {bike.geometries.map((geo, index) => {
                    const inCompare = isInComparison(bike.id, geo.size_label);
                    return (
                      <td
                        key={`${bike.id}-${geo.size_label}-${index}-action`}
                        className="py-4 px-6 text-center border-r"
                      >
                        <button
                          onClick={() =>
                            inCompare
                              ? removeFromCompare(bike.id, geo.size_label)
                              : addToCompare(bike, geo)
                          }
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors w-full ${
                            inCompare
                              ? "bg-red-100 text-red-600 hover:bg-red-200"
                              : "bg-blue-100 text-blue-600 hover:bg-blue-200"
                          }`}
                        >
                          {inCompare
                            ? t.ui.remove_from_compare
                            : t.ui.add_to_compare}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
