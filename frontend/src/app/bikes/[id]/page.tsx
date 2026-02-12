"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import BikeFrameSVG from "../../../components/BikeFrameSVG";
import { FrameDefinition } from "../../../types";
import { useLanguage } from "../../../context/LanguageContext";
import { useComparison } from "../../../context/ComparisonContext";
import LanguageSwitcher from "../../../components/LanguageSwitcher";
import { useRouter } from "next/navigation";

function BikeDetailContent() {
  const { id } = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { t } = useLanguage();
  const { addToCompare, removeFromCompare, isInComparison, comparisonList } =
    useComparison();
  const [group, setGroup] = useState<FrameDefinition | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBike = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/bikes/definitions/${id}`,
        );
        if (!res.ok) throw new Error("Failed to fetch bike details");
        const data: FrameDefinition = await res.json();
        setGroup(data);
        if (data.geometries && data.geometries.length > 0) {
          // If the 'size' in URL is one of the geometries, select it
          const sizeId = searchParams.get("size");
          const targetId = sizeId ? Number(sizeId) : null;

          const found = targetId
            ? data.geometries.find((g) => g.id === targetId)
            : null;
          setSelectedProductId(found ? found.id : data.geometries[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchBike();
  }, [id, searchParams]);

  const handleDelete = async () => {
    if (!selectedProductId) return;
    if (!confirm(t.ui.delete_bike + "?")) return;
    setDeleting(true);
    try {
      const res = await fetch(
        `http://localhost:8000/api/bikes/specs/${selectedProductId}`,
        {
          method: "DELETE",
        },
      );
      if (!res.ok) throw new Error("Failed to delete bike");
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setDeleting(false);
    }
  };

  if (loading) return <div className="text-center py-20">{t.ui.loading}</div>;
  if (error)
    return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!group || !selectedProductId)
    return (
      <div className="text-center py-20">{t.categories.bike_not_found}</div>
    );

  const geometry =
    group.geometries?.find((g) => g.id === selectedProductId) ||
    group.geometries?.[0];

  if (!geometry)
    return (
      <div className="text-center py-20">{t.categories.bike_not_found}</div>
    );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex justify-between items-center mb-8">
          <Link
            href="/"
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
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
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors shadow-sm disabled:bg-red-400"
            >
              {deleting ? t.ui.deleting : t.ui.delete_bike}
            </button>
          </div>
        </div>

        <header className="mb-8">
          <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white">
            {group.brand_name} {group.model_name}
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mt-2">
            {group.category} {group.year_start && `(${group.year_start})`}
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-4 mb-8 bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm"></div>

        <div className="bg-white dark:bg-gray-900 p-8 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm mb-12 flex justify-center">
          <BikeFrameSVG geometry={geometry} height={200} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
              {t.ui.brand}
            </h3>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {group.brand_name}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
              {t.ui.material}
            </h3>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {group.material || "N/A"}
            </p>
          </div>
        </div>

        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100 dark:border-gray-800">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              {t.ui.geometry_details}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 uppercase text-xs font-semibold border-b dark:border-gray-800">
                  <th className="py-4 px-6 border-r dark:border-gray-800 sticky left-0 bg-gray-50 dark:bg-gray-800 z-10 w-48">
                    {t.ui.geometry_details}
                  </th>
                  {group.geometries?.map((g) => (
                    <th
                      key={g.id}
                      className={`py-4 px-6 text-center border-r dark:border-gray-800 min-w-[120px] cursor-pointer transition-colors ${
                        selectedProductId === g.id
                          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                          : "hover:bg-gray-100 dark:hover:bg-gray-800"
                      }`}
                      onClick={() => setSelectedProductId(g.id)}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-base font-bold text-gray-900 dark:text-white normal-case">
                          {g.size_label}
                        </span>
                        {selectedProductId === g.id && (
                          <span className="text-[10px] bg-blue-600 text-white px-2 py-0.5 rounded-full uppercase">
                            Selected
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {(
                  [
                    "stack_mm",
                    "reach_mm",
                    "top_tube_effective_mm",
                    "seat_tube_length_mm",
                    "head_tube_length_mm",
                    "chainstay_length_mm",
                    "head_tube_angle",
                    "seat_tube_angle",
                    "wheelbase_mm",
                  ] as (keyof typeof t.geometry)[]
                ).map((key) => (
                  <tr
                    key={key}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="py-3 px-6 font-medium text-gray-500 dark:text-gray-400 bg-gray-50/30 dark:bg-gray-800/10 border-r dark:border-gray-800 sticky left-0 z-10">
                      {t.geometry[key]}
                    </td>
                    {group.geometries?.map((g) => (
                      <td
                        key={g.id}
                        className={`py-3 px-6 text-center border-r dark:border-gray-800 font-mono ${
                          selectedProductId === g.id
                            ? "bg-blue-50/30 dark:bg-blue-900/10 text-blue-700 dark:text-blue-400 font-bold"
                            : "text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        {g[key as keyof typeof g] as string | number}
                        {String(key).includes("angle") ? "°" : " mm"}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="py-4 px-6 font-medium text-gray-500 dark:text-gray-400 bg-gray-50/30 dark:bg-gray-800/10 border-r dark:border-gray-800 sticky left-0 z-10">
                    {t.ui.compare}
                  </td>
                  {group.geometries?.map((g) => {
                    const inCompare = isInComparison(g.id);
                    return (
                      <td
                        key={g.id}
                        className={`py-4 px-6 text-center border-r dark:border-gray-800 ${
                          selectedProductId === g.id
                            ? "bg-blue-50/30 dark:bg-blue-900/10"
                            : ""
                        }`}
                      >
                        <button
                          onClick={() =>
                            inCompare
                              ? removeFromCompare(g.id)
                              : addToCompare(g)
                          }
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors w-full ${
                            inCompare
                              ? "bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/40"
                              : "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
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

export default function BikeDetailPage() {
  return (
    <Suspense fallback={<div className="text-center py-20">Loading...</div>}>
      <BikeDetailContent />
    </Suspense>
  );
}
