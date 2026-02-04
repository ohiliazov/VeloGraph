"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bike, Geometry } from "@/types";
import { useLanguage } from "@/context/LanguageContext";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function NewBikePage() {
  const router = useRouter();
  const { t } = useLanguage();

  const [bike, setBike] = useState<Partial<Bike>>({
    brand: "",
    model_name: "",
    model_year: new Date().getFullYear(),
    categories: [],
    geometries: [
      {
        size_label: "M",
        stack: 0,
        reach: 0,
        top_tube_effective_length: 0,
        seat_tube_length: 0,
        head_tube_length: 0,
        chainstay_length: 0,
        head_tube_angle: 70,
        seat_tube_angle: 73,
        bb_drop: 0,
        wheelbase: 0,
      },
    ],
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setBike({ ...bike, [name]: value });
  };

  const handleGeometryChange = (
    index: number,
    field: keyof Geometry,
    value: string | number,
  ) => {
    const newGeometries = [...(bike.geometries || [])];
    newGeometries[index] = { ...newGeometries[index], [field]: value };
    setBike({ ...bike, geometries: newGeometries });
  };

  const addGeometry = () => {
    const last = bike.geometries?.[bike.geometries.length - 1];
    const next: Geometry = last
      ? { ...last }
      : {
          size_label: "",
          stack: 0,
          reach: 0,
          top_tube_effective_length: 0,
          seat_tube_length: 0,
          head_tube_length: 0,
          chainstay_length: 0,
          head_tube_angle: 70,
          seat_tube_angle: 73,
          bb_drop: 0,
          wheelbase: 0,
        };
    setBike({ ...bike, geometries: [...(bike.geometries || []), next] });
  };

  const removeGeometry = (index: number) => {
    if ((bike.geometries?.length || 0) <= 1) return;
    const next = [...(bike.geometries || [])];
    next.splice(index, 1);
    setBike({ ...bike, geometries: next });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      // Use arbitrary user_id as requested
      const payload = { ...bike, user_id: "user_123", source_url: "" };
      const res = await fetch(`http://localhost:8000/api/bikes/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to create bike");
      }
      const created = await res.json();
      router.push(`/bikes/${created.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An error occurred while saving",
      );
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex justify-between items-center mb-8">
          <Link href="/" className="text-blue-600 hover:underline">
            ← {t.ui.back_to_search}
          </Link>
          <LanguageSwitcher />
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          {t.ui.create_bike}
        </h1>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg">
            {error}
          </div>
        )}

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
                  {t.geometry.colors}
                </label>
                <input
                  type="text"
                  name="color"
                  value={bike.color || ""}
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
                  value={bike.categories?.join(", ")}
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
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">
                  {t.ui.max_tire_width} (mm)
                </label>
                <input
                  type="number"
                  name="max_tire_width"
                  value={bike.max_tire_width || ""}
                  onChange={handleInputChange}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="e.g. 45"
                />
              </div>
            </div>
          </section>

          <section className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <div className="flex justify-between items-center border-b pb-2">
              <h2 className="text-xl font-semibold text-gray-800">
                {t.ui.geometries}
              </h2>
              <button
                type="button"
                onClick={addGeometry}
                className="text-sm bg-blue-50 text-blue-600 px-3 py-1 rounded hover:bg-blue-100 transition-colors"
              >
                + Add Size
              </button>
            </div>
            <div className="overflow-x-auto">
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
                    <th className="py-2 px-1 text-left">
                      {t.geometry.bb_drop}
                    </th>
                    <th className="py-2 px-1 text-left">
                      {t.geometry.wheelbase}
                    </th>
                    <th className="py-2 px-1 text-left"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {bike.geometries?.map((geo, index) => (
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
                          required
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
                      <td className="py-2 px-1">
                        <button
                          type="button"
                          onClick={() => removeGeometry(index)}
                          className="text-red-500 hover:text-red-700"
                          title="Remove Size"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="flex justify-end gap-4">
            <Link
              href="/"
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
