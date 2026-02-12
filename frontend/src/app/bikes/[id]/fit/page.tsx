"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import BikeFrameSVG from "@/components/BikeFrameSVG";
import { BikeDefinition } from "@/types";
import LanguageSwitcher from "@/components/LanguageSwitcher";

// Fit page: interactive overlay of personal fit points over the bike SVG
// Markers reference:
// - BB is origin (0,0) in user inputs (mm). For SVG transform we adapt to the frame math where BB.y = -bb_drop
// - Saddle point: (x = -setback, y = saddleHeight)
// - Handlebar point: (x = handlebarReach, y = saddleHeight - handlebarDrop)

function FitContent() {
  const { id } = useParams();
  const searchParams = useSearchParams();

  const [group, setGroup] = useState<BikeDefinition | null>(null);
  const [selectedSpecId, setSelectedSpecId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // User inputs (in mm)
  const [saddleHeight, setSaddleHeight] = useState<number>(730);
  const [saddleSetback, setSaddleSetback] = useState<number>(50);
  const [barReach, setBarReach] = useState<number>(500);
  const [barDrop, setBarDrop] = useState<number>(70);
  const [showStackReach, setShowStackReach] = useState<boolean>(true);

  // Visualization constants matched with BikeFrameSVG
  const MARGIN_PX = 10;
  const DEFAULT_WHEEL_DIAMETER_MM = 622;
  const DEFAULT_TIRE_WIDTH_MM = 30;
  const RIM_DEPTH_MM = 30; // not used but kept for parity
  const DEFAULT_SCALE = 0.35; // used only when no explicit height/width given
  const heightPx = 260; // chosen fixed height like in detail page (200) but slightly larger for fit

  useEffect(() => {
    const fetchBike = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/bikes/definitions/${id}`,
        );
        if (!res.ok) throw new Error("Failed to fetch bike details");
        const data: BikeDefinition = await res.json();
        setGroup(data);
        if (data.geometries && data.geometries.length > 0) {
          const sizeId = searchParams.get("size");
          const targetId = sizeId ? Number(sizeId) : null;
          const found = targetId
            ? data.geometries.find((g) => g.id === targetId)
            : null;
          setSelectedSpecId(found ? found.id : data.geometries[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchBike();
  }, [id, searchParams]);

  const geometry = useMemo(() => {
    if (!group || !selectedSpecId) return null;
    return (
      group.geometries?.find((g) => g.id === selectedSpecId) ||
      group.geometries?.[0] ||
      null
    );
  }, [group, selectedSpecId]);

  // Compute the same transform as BikeFrameSVG to align our overlay
  const overlay = useMemo(() => {
    if (!geometry) return null;

    const stack = geometry.stack_mm;
    const reach = geometry.reach_mm;
    const bb_drop = geometry.bb_drop_mm;
    const chainstay = geometry.chainstay_length_mm;
    const seatTube = geometry.seat_tube_length_mm || 500;
    const seatAngle = geometry.seat_tube_angle;
    const headTube = geometry.head_tube_length_mm || 150;
    const headAngle = geometry.head_tube_angle;
    const wheelbase = geometry.wheelbase_mm;

    // math points used by BikeFrameSVG
    const headTop: [number, number] = [reach, stack - bb_drop];
    const headBottom: [number, number] = [
      headTop[0] + headTube * Math.cos((headAngle * Math.PI) / 180),
      headTop[1] - headTube * Math.sin((headAngle * Math.PI) / 180),
    ];

    const points = {
      bb: [0, -bb_drop] as [number, number],
      rear_axle: [-chainstay, 0] as [number, number],
      front_axle: [wheelbase - chainstay, 0] as [number, number],
      seat_top: [
        -seatTube * Math.cos((seatAngle * Math.PI) / 180),
        seatTube * Math.sin((seatAngle * Math.PI) / 180) - bb_drop,
      ] as [number, number],
      head_top: headTop,
      head_bottom: headBottom,
    };

    const wheelDiameter = DEFAULT_WHEEL_DIAMETER_MM;
    const tireWidth = DEFAULT_TIRE_WIDTH_MM;
    const wheelRadius = (wheelDiameter + tireWidth) / 2;

    const xs = [
      points.rear_axle[0] - wheelRadius,
      points.front_axle[0] + wheelRadius,
      points.seat_top[0],
      points.head_top[0],
      points.head_bottom[0],
      points.bb[0],
    ];
    const ys = [
      points.rear_axle[1] - wheelRadius,
      points.rear_axle[1] + wheelRadius,
      points.seat_top[1],
      points.head_top[1],
      points.head_bottom[1],
      points.bb[1],
      0,
    ];

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const widthMM = Math.max(maxX - minX, 1);
    const heightMM = Math.max(maxY - minY, 1);

    // Scale behavior mirrors BikeFrameSVG when only height is provided
    const availableH = heightPx - 2 * MARGIN_PX;
    let currentScale = availableH / heightMM;
    if (!isFinite(currentScale) || currentScale <= 0) {
      currentScale = Math.max(DEFAULT_SCALE, 0.01);
    }

    const svgW = widthMM * currentScale + 2 * MARGIN_PX;
    const svgH = heightPx; // we supplied fixed height

    const offsetX = (svgW - widthMM * currentScale - 2 * MARGIN_PX) / 2;
    const offsetY = (svgH - heightMM * currentScale - 2 * MARGIN_PX) / 2;

    const tx = MARGIN_PX + offsetX - minX * currentScale;
    const ty = MARGIN_PX + offsetY + maxY * currentScale;

    const toPx = (pt: [number, number]) =>
      [tx + pt[0] * currentScale, ty - pt[1] * currentScale] as [
        number,
        number,
      ];

    // Convenience important frame points in px
    const pBB = toPx(points.bb);
    const pHeadTop = toPx(points.head_top);

    return {
      toPx,
      svgW,
      svgH,
      pBB,
      pHeadTop,
      bb_drop,
      stack,
      reach,
    };
  }, [geometry]);

  if (loading) return <div className="text-center py-20">Loading...</div>;
  if (error)
    return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!group || !geometry || !overlay)
    return <div className="text-center py-20">Bike not found</div>;

  // Fit points in bike-math mm space (relative to BB at 0,0). Convert to BikeFrameSVG math by adjusting Y with -bb_drop
  const saddleMath: [number, number] = [
    -saddleSetback,
    saddleHeight - overlay.bb_drop,
  ];
  const barsMath: [number, number] = [
    barReach,
    saddleHeight - barDrop - overlay.bb_drop,
  ];

  const saddlePx = overlay.toPx(saddleMath);
  const barsPx = overlay.toPx(barsMath);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex justify-between items-center mb-6">
          <Link
            href={`/bikes/${group.id}?size=${geometry.id}`}
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            ← Back to bike
          </Link>
          <div className="flex items-center gap-4">
            <LanguageSwitcher />
          </div>
        </div>

        <header className="mb-6">
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white">
            {group.brand_name} {group.model_name} · Fit Visualizer
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Size: {geometry.size_label} · Stack {geometry.stack_mm} / Reach{" "}
            {geometry.reach_mm}
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Visualization */}
          <div className="lg:col-span-2">
            <div
              className="relative bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden"
              style={{ width: Math.ceil(overlay.svgW), height: heightPx }}
            >
              {/* Base Frame */}
              <BikeFrameSVG geometry={geometry} height={heightPx} />
              {/* Overlay */}
              <svg
                className="absolute inset-0 pointer-events-none"
                width={overlay.svgW}
                height={overlay.svgH}
                viewBox={`0 0 ${overlay.svgW} ${overlay.svgH}`}
              >
                {/* Optional original stack/reach lines */}
                {showStackReach && (
                  <g>
                    {/* Vertical (stack) from BB up */}
                    <line
                      x1={overlay.pBB[0]}
                      y1={overlay.pBB[1]}
                      x2={overlay.pBB[0]}
                      y2={
                        overlay.toPx([
                          0,
                          geometry.stack_mm - geometry.bb_drop_mm,
                        ])[1]
                      }
                      stroke="#38bdf8"
                      strokeWidth={2}
                      strokeDasharray="6 6"
                      opacity={0.7}
                    />
                    {/* Horizontal (reach) to head-top projection */}
                    <line
                      x1={overlay.pBB[0]}
                      y1={
                        overlay.toPx([
                          0,
                          geometry.stack_mm - geometry.bb_drop_mm,
                        ])[1]
                      }
                      x2={
                        overlay.toPx([
                          geometry.reach_mm,
                          geometry.stack_mm - geometry.bb_drop_mm,
                        ])[0]
                      }
                      y2={
                        overlay.toPx([
                          0,
                          geometry.stack_mm - geometry.bb_drop_mm,
                        ])[1]
                      }
                      stroke="#38bdf8"
                      strokeWidth={2}
                      strokeDasharray="6 6"
                      opacity={0.7}
                    />
                    {/* Head-top indicator */}
                    <circle
                      cx={overlay.pHeadTop[0]}
                      cy={overlay.pHeadTop[1]}
                      r={4}
                      fill="#38bdf8"
                    />
                  </g>
                )}

                {/* Measurement lines from BB to fit points */}
                <g>
                  <line
                    x1={overlay.pBB[0]}
                    y1={overlay.pBB[1]}
                    x2={saddlePx[0]}
                    y2={saddlePx[1]}
                    stroke="#fb923c" /* orange-400 */
                    strokeWidth={2}
                    strokeDasharray="4 6"
                    opacity={0.9}
                  />
                  <line
                    x1={overlay.pBB[0]}
                    y1={overlay.pBB[1]}
                    x2={barsPx[0]}
                    y2={barsPx[1]}
                    stroke="#06b6d4" /* cyan-500 */
                    strokeWidth={2}
                    strokeDasharray="4 6"
                    opacity={0.9}
                  />
                </g>

                {/* Markers */}
                <g>
                  <circle
                    cx={saddlePx[0]}
                    cy={saddlePx[1]}
                    r={6}
                    fill="#f97316"
                  />
                  <circle cx={barsPx[0]} cy={barsPx[1]} r={6} fill="#06b6d4" />
                </g>
              </svg>
            </div>

            {/* Size selector */}
            <div className="mt-4 flex flex-wrap gap-2">
              {group.geometries?.map((g) => (
                <button
                  key={g.id}
                  onClick={() => setSelectedSpecId(g.id)}
                  className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                    selectedSpecId === g.id
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {g.size_label}
                </button>
              ))}
            </div>
          </div>

          {/* Sidebar inputs */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-5">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Fit Input
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Saddle Height (BB → saddle top)
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm"
                  value={saddleHeight}
                  onChange={(e) => setSaddleHeight(Number(e.target.value) || 0)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Saddle Setback (BB → saddle nose, horizontal)
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm"
                  value={saddleSetback}
                  onChange={(e) =>
                    setSaddleSetback(Number(e.target.value) || 0)
                  }
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Handlebar Reach (BB → bar center, horizontal)
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm"
                  value={barReach}
                  onChange={(e) => setBarReach(Number(e.target.value) || 0)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Handlebar Drop (saddle top → bar center, vertical)
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm"
                  value={barDrop}
                  onChange={(e) => setBarDrop(Number(e.target.value) || 0)}
                />
              </div>

              <label className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  checked={showStackReach}
                  onChange={(e) => setShowStackReach(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Show frame stack/reach lines
                </span>
              </label>

              <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-gray-600 dark:text-gray-400">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 border border-gray-200 dark:border-gray-700">
                  <div className="font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">
                    Saddle point
                  </div>
                  <div>X: {-saddleSetback} mm</div>
                  <div>Y: {saddleHeight} mm</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 border border-gray-200 dark:border-gray-700">
                  <div className="font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">
                    Bar center
                  </div>
                  <div>X: {barReach} mm</div>
                  <div>Y: {saddleHeight - barDrop} mm</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FitPage() {
  return (
    <Suspense fallback={<div className="text-center py-20">Loading...</div>}>
      <FitContent />
    </Suspense>
  );
}
