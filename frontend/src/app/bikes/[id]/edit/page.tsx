"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Bike, Geometry } from "../../../../types";
import { useLanguage } from "../../../../context/LanguageContext";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";

export default function BikeEditPage() {
  const { id } = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const [bike, setBike] = useState<Bike | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    if (!bike) return;
    const { name, value } = e.target;
    setBike({ ...bike, [name]: value });
  };

  const handleGeometryChange = (
    index: number,
    field: keyof Geometry,
    value: string | number,
  ) => {
    if (!bike) return;
    const newGeometries = [...bike.geometries];
    newGeometries[index] = { ...newGeometries[index], [field]: value };
    setBike({ ...bike, geometries: newGeometries });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bike) return;
    setSaving(true);
    try {
      const res = await fetch(`http://localhost:8000/api/bikes/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bike),
      });
      if (!res.ok) throw new Error("Failed to save bike details");
      router.push(`/bikes/${id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An error occurred while saving",
      );
      setSaving(false);
    }
  };

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
          <Link href={`/bikes/${id}`} className="text-blue-600 hover:underline">
            ← {t.ui.back_to_details}
          </Link>
          <LanguageSwitcher />
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          {t.ui.edit} {bike.brand} {bike.model_name}
        </h1>

        <form onSubmit={handleSave} className="space-y-8">
          <section className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-xl font-semibold text-gray-800 border-b pb-2">
              {t.ui.metadata}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.brand}
                </label>
                <input
                  type="text"
                  name="brand"
                  value={bike.brand}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.model}
                </label>
                <input
                  type="text"
                  name="model_name"
                  value={bike.model_name}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.year}
                </label>
                <input
                  type="number"
                  name="model_year"
                  value={bike.model_year || ""}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.material}
                </label>
                <input
                  type="text"
                  name="frame_material"
                  value={bike.frame_material || ""}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.wheel_size}
                </label>
                <input
                  type="text"
                  name="wheel_size"
                  value={bike.wheel_size || ""}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.brake_type}
                </label>
                <input
                  type="text"
                  name="brake_type"
                  value={bike.brake_type || ""}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.categories_comma_hint}
                </label>
                <input
                  type="text"
                  name="categories"
                  value={bike.categories.join(", ")}
                  onChange={(e) => {
                    const value = e.target.value;
                    const cats = value
                      .split(",")
                      .map((c) => c.trim())
                      .filter((c) => c !== "");
                    setBike({ ...bike, categories: cats });
                  }}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
          </section>

          <section className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4 overflow-x-auto">
            <h2 className="text-xl font-semibold text-gray-800 border-b pb-2">
              {t.ui.geometries}
            </h2>
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b">
                  <th className="py-2 px-1 text-left">
                    {t.geometry.size_label}
                  </th>
                  <th className="py-2 px-1 text-left">{t.geometry.stack}</th>
                  <th className="py-2 px-1 text-left">{t.geometry.reach}</th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.top_tube_effective_length}
                  </th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.seat_tube_length}
                  </th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.head_tube_length}
                  </th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.chainstay_length}
                  </th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.head_tube_angle}
                  </th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.seat_tube_angle}
                  </th>
                  <th className="py-2 px-1 text-left">{t.geometry.bb_drop}</th>
                  <th className="py-2 px-1 text-left">
                    {t.geometry.wheelbase}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {bike.geometries.map((geo, index) => (
                  <tr key={index}>
                    <td className="py-2 px-1">
                      <input
                        type="text"
                        value={geo.size_label}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "size_label",
                            e.target.value,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.stack}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "stack",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.reach}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "reach",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.top_tube_effective_length}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "top_tube_effective_length",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.seat_tube_length}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "seat_tube_length",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.head_tube_length}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "head_tube_length",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.chainstay_length}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "chainstay_length",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        step="0.1"
                        value={geo.head_tube_angle}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "head_tube_angle",
                            parseFloat(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        step="0.1"
                        value={geo.seat_tube_angle}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "seat_tube_angle",
                            parseFloat(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.bb_drop}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "bb_drop",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        value={geo.wheelbase}
                        onChange={(e) =>
                          handleGeometryChange(
                            index,
                            "wheelbase",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        className="w-16 p-1 border rounded"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="flex justify-end gap-4">
            <Link
              href={`/bikes/${id}`}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
            >
              {t.ui.cancel}
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              {saving ? t.ui.saving : t.ui.save}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
