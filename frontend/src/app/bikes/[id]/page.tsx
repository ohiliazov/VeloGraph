"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import BikeFrameSVG from "../../../components/BikeFrameSVG";
import { BikeGroup } from "../../../types";
import { useLanguage } from "../../../context/LanguageContext";
import { useComparison } from "../../../context/ComparisonContext";
import LanguageSwitcher from "../../../components/LanguageSwitcher";
import { useRouter } from "next/navigation";

export default function BikeDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const { addToCompare, removeFromCompare, isInComparison, comparisonList } =
    useComparison();
  const [group, setGroup] = useState<BikeGroup | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBike = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/bikes/${id}`);
        if (!res.ok) throw new Error("Failed to fetch bike details");
        const data: BikeGroup = await res.json();
        setGroup(data);
        if (data.products.length > 0) {
          // If the ID in URL is one of the products, select it, otherwise first one
          const currentId = Number(id);
          const found = data.products.find((p) => p.id === currentId);
          setSelectedProductId(found ? found.id : data.products[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchBike();
  }, [id]);

  const handleDelete = async () => {
    if (!selectedProductId) return;
    if (!confirm(t.ui.delete_bike + "?")) return;
    setDeleting(true);
    try {
      const res = await fetch(
        `http://localhost:8000/api/bikes/${selectedProductId}`,
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

  const product =
    group.products.find((p) => p.id === selectedProductId) || group.products[0];
  const geometry = product.geometry_spec;

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
            {group.family.brand_name} {group.family.family_name}
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mt-2">
            {group.definition.name}{" "}
            {group.definition.year_start && `(${group.definition.year_start})`}
          </p>
          <p className="text-lg text-gray-400 dark:text-gray-500 mt-1 font-mono uppercase tracking-tight">
            SKU: {product.sku}
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-4 mb-8 bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
          {product.colors.length > 0 && (
            <div className="flex-1 min-w-[200px]">
              <span className="block text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-2">
                Available Colors
              </span>
              <div className="flex flex-wrap gap-3">
                {product.colors.map((colorLabel, idx) => {
                  const colorMap: Record<string, string> = {
                    black: "#000000",
                    czarny: "#000000",
                    white: "#ffffff",
                    bialy: "#ffffff",
                    biały: "#ffffff",
                    red: "#ef4444",
                    czerwony: "#ef4444",
                    blue: "#3b82f6",
                    niebieski: "#3b82f6",
                    green: "#22c55e",
                    zielony: "#22c55e",
                    gray: "#6b7280",
                    grey: "#6b7280",
                    szary: "#6b7280",
                    silver: "#9ca3af",
                    srebrny: "#9ca3af",
                    orange: "#f97316",
                    pomarańczowy: "#f97316",
                    pomaranczowy: "#f97316",
                    yellow: "#facc15",
                    zolty: "#facc15",
                    żółty: "#facc15",
                    purple: "#a855f7",
                    fioletowy: "#a855f7",
                  };
                  const key = (colorLabel || "")
                    .toLowerCase()
                    .split(/[\s-]+/)[0];
                  const bg = colorMap[key] || "#ddd";
                  return (
                    <div
                      key={idx}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 shadow-sm hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
                    >
                      <span
                        className="w-3.5 h-3.5 rounded-full border border-gray-300 dark:border-gray-600 shadow-inner"
                        style={{ backgroundColor: bg }}
                      />
                      <span className="text-[11px] font-medium">
                        {colorLabel}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-900 p-8 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm mb-12 flex justify-center">
          <BikeFrameSVG geometry={geometry} height={200} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
              {t.ui.brand}
            </h3>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {group.family.brand_name}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
              {t.ui.material}
            </h3>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {group.definition.material || "N/A"}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
              Build Kit
            </h3>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {product.build_kit.name}
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
                  {group.products.map((p) => (
                    <th
                      key={p.id}
                      className={`py-4 px-6 text-center border-r dark:border-gray-800 min-w-[120px] cursor-pointer transition-colors ${
                        selectedProductId === p.id
                          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                          : "hover:bg-gray-100 dark:hover:bg-gray-800"
                      }`}
                      onClick={() => setSelectedProductId(p.id)}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-base font-bold text-gray-900 dark:text-white normal-case">
                          {p.geometry_spec.size_label}
                        </span>
                        {selectedProductId === p.id && (
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
                    {group.products.map((p) => (
                      <td
                        key={p.id}
                        className={`py-3 px-6 text-center border-r dark:border-gray-800 font-mono ${
                          selectedProductId === p.id
                            ? "bg-blue-50/30 dark:bg-blue-900/10 text-blue-700 dark:text-blue-400 font-bold"
                            : "text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        {
                          p.geometry_spec[
                            key as keyof typeof p.geometry_spec
                          ] as string | number
                        }
                        {String(key).includes("angle") ? "°" : " mm"}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="py-4 px-6 font-medium text-gray-500 dark:text-gray-400 bg-gray-50/30 dark:bg-gray-800/10 border-r dark:border-gray-800 sticky left-0 z-10">
                    {t.ui.compare}
                  </td>
                  {group.products.map((p) => {
                    const inCompare = isInComparison(p.id);
                    return (
                      <td
                        key={p.id}
                        className={`py-4 px-6 text-center border-r dark:border-gray-800 ${
                          selectedProductId === p.id
                            ? "bg-blue-50/30 dark:bg-blue-900/10"
                            : ""
                        }`}
                      >
                        <button
                          onClick={() =>
                            inCompare
                              ? removeFromCompare(p.id)
                              : addToCompare(p)
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
