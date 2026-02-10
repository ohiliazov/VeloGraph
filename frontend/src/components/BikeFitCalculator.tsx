"use client";

import React, { useMemo, useState } from "react";

// Riding styles and constants
const STYLES = [
  "Aggressive (Race)",
  "Balanced (All-Rounder)",
  "Comfort (Endurance)",
] as const;
type RidingStyle = (typeof STYLES)[number];

const COCKPIT_CONST: Record<RidingStyle, number> = {
  "Aggressive (Race)": 4,
  "Balanced (All-Rounder)": 2,
  "Comfort (Endurance)": 0,
};

const STACK_REACH_TARGET: Record<
  RidingStyle,
  { label: string; min?: number; max?: number }
> = {
  "Aggressive (Race)": { label: "< 1.45", max: 1.45 },
  "Balanced (All-Rounder)": { label: "1.45 – 1.55", min: 1.45, max: 1.55 },
  "Comfort (Endurance)": { label: "> 1.55", min: 1.55 },
};

function classNames(...c: (string | false | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export default function BikeFitCalculator() {
  const [inseam, setInseam] = useState<number | "">(82);
  const [torso, setTorso] = useState<number | "">(60);
  const [arm, setArm] = useState<number | "">(60);
  const [style, setStyle] = useState<RidingStyle>("Balanced (All-Rounder)");

  // Optional: user can enter actual frame stack & reach to get a verdict
  const [stack, setStack] = useState<number | "">(540);
  const [reach, setReach] = useState<number | "">(380);

  // UI focus for highlighting parts in SVG
  const [focus, setFocus] = useState<"saddle" | "frame" | "cockpit">("saddle");

  // Derived calculations
  const saddleHamley = useMemo(
    () => (typeof inseam === "number" ? inseam * 1.09 : null),
    [inseam],
  );
  const saddleLeMond = useMemo(
    () => (typeof inseam === "number" ? inseam * 0.883 : null),
    [inseam],
  );
  const saddle105 = useMemo(
    () => (typeof inseam === "number" ? inseam * 1.05 : null),
    [inseam],
  );

  const cockpitReach = useMemo(() => {
    if (typeof torso !== "number" || typeof arm !== "number") return null;
    const c = COCKPIT_CONST[style];
    return (torso + arm) / 2 + c;
  }, [torso, arm, style]);

  const targetSR = STACK_REACH_TARGET[style];

  const actualSR = useMemo(() => {
    if (typeof stack === "number" && typeof reach === "number" && reach > 0) {
      return stack / reach;
    }
    return null;
  }, [stack, reach]);

  const verdict = useMemo(() => {
    if (actualSR == null)
      return {
        text: `Target S/R ${targetSR.label}`,
        level: "neutral" as const,
      };
    const { min, max } = targetSR;
    if (min != null && actualSR < min)
      return {
        text: "Fit tends toward aggressive (low S/R)",
        level: "warning" as const,
      };
    if (max != null && actualSR > max)
      return {
        text: "Fit tends toward upright (high S/R)",
        level: "warning" as const,
      };
    return {
      text: "Within target range for selected style",
      level: "good" as const,
    };
  }, [actualSR, targetSR]);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h2 className="text-3xl font-semibold text-gray-900 dark:text-white">
          Bike Fit Coordinate Calculator
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Responsive and interactive. Values update in real time.
        </p>
      </div>

      {/* Riding style toggle */}
      <div className="mb-6">
        <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden bg-white dark:bg-zinc-900">
          {STYLES.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={classNames(
                "px-4 py-2 text-sm font-medium transition-colors",
                style === s
                  ? "bg-blue-600 text-white"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800",
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Inputs grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <NumberField
          label="Inseam (cm)"
          value={inseam}
          onChange={setInseam}
          onFocus={() => setFocus("saddle")}
        />
        <NumberField
          label="Torso Length (cm)"
          value={torso}
          onChange={setTorso}
          onFocus={() => setFocus("cockpit")}
        />
        <NumberField
          label="Arm Length (cm)"
          value={arm}
          onChange={setArm}
          onFocus={() => setFocus("cockpit")}
        />
      </div>

      {/* Optional bike stack & reach to evaluate fit verdict */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <NumberField
          label="Bike Stack (mm, optional)"
          value={stack}
          onChange={setStack}
          onFocus={() => setFocus("frame")}
        />
        <NumberField
          label="Bike Reach (mm, optional)"
          value={reach}
          onChange={setReach}
          onFocus={() => setFocus("frame")}
        />
      </div>

      {/* Visual diagram + results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* SVG Diagram */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-zinc-900 p-4">
          <SimpleBikeSVG focus={focus} />
          <div className="mt-4 flex gap-2 text-xs text-gray-500 dark:text-gray-400">
            <LegendSwatch
              color="#f59e0b"
              label="Saddle / Seat Tube"
              active={focus === "saddle"}
              onHover={() => setFocus("saddle")}
            />
            <LegendSwatch
              color="#3b82f6"
              label="Front End / Stack-Reach"
              active={focus === "frame"}
              onHover={() => setFocus("frame")}
            />
            <LegendSwatch
              color="#10b981"
              label="Cockpit / Reach"
              active={focus === "cockpit"}
              onHover={() => setFocus("cockpit")}
            />
          </div>
        </div>

        {/* Results */}
        <div className="space-y-6">
          {/* Fit verdict */}
          <div
            className={classNames(
              "rounded-xl border p-4",
              verdict.level === "good"
                ? "border-emerald-300/30 bg-emerald-500/10 text-emerald-400"
                : verdict.level === "warning"
                  ? "border-amber-300/30 bg-amber-500/10 text-amber-400"
                  : "border-gray-200 dark:border-gray-800 bg-white dark:bg-zinc-900 text-gray-700 dark:text-gray-300",
            )}
          >
            <div className="text-sm font-medium">Fit Verdict</div>
            <div className="text-lg font-semibold mt-1">{verdict.text}</div>
            <div className="text-xs opacity-80 mt-1 text-gray-500 dark:text-gray-400">
              Target S/R for {style}: {targetSR.label}
              {actualSR != null && (
                <span className="ml-2">
                  • Your bike S/R: {actualSR.toFixed(2)}
                </span>
              )}
            </div>
          </div>

          {/* Saddle heights table */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
            <div className="bg-gray-50 dark:bg-zinc-900/60 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200">
              Saddle Height Recommendations (from BB to top of saddle)
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-800 text-sm">
              <Row
                label="Hamley (Inseam × 1.09)"
                value={saddleHamley}
                unit="cm"
              />
              <Row
                label="LeMond (Inseam × 0.883)"
                value={saddleLeMond}
                unit="cm"
              />
              <Row
                label="105% Rule (Inseam × 1.05)"
                value={saddle105}
                unit="cm"
              />
            </div>
          </div>

          {/* Cockpit reach */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-200">
              Estimated Cockpit Reach
            </div>
            <div className="text-2xl font-semibold mt-1 text-gray-900 dark:text-white">
              {cockpitReach != null ? `${cockpitReach.toFixed(1)} cm` : "—"}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Formula: ((Torso + Arm) / 2) + constant. Constants — Race: 4,
              Balanced: 2, Comfort: 0.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  onFocus,
}: {
  label: string;
  value: number | "";
  onChange: (v: number | "") => void;
  onFocus?: () => void;
}) {
  return (
    <label className="block">
      <span className="block text-sm text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </span>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") onChange("");
          else onChange(Number(v));
        }}
        onFocus={onFocus}
        className="w-full rounded-lg bg-white dark:bg-zinc-900 border border-gray-200 dark:border-gray-800 px-3 py-2 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="0"
      />
    </label>
  );
}

function Row({
  label,
  value,
  unit,
}: {
  label: string;
  value: number | null;
  unit: string;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2">
      <div className="text-gray-700 dark:text-gray-300">{label}</div>
      <div className="font-medium text-gray-900 dark:text-white">
        {value != null ? `${value.toFixed(1)} ${unit}` : "—"}
      </div>
    </div>
  );
}

function LegendSwatch({
  color,
  label,
  active,
  onHover,
}: {
  color: string;
  label: string;
  active?: boolean;
  onHover?: () => void;
}) {
  return (
    <div
      onMouseEnter={onHover}
      className={classNames(
        "flex items-center gap-2 px-2 py-1 rounded cursor-default border",
        active
          ? "border-current text-current"
          : "border-transparent text-gray-500 dark:text-gray-400",
      )}
      style={active ? { color } : undefined}
    >
      <span
        className="inline-block w-3 h-3 rounded-sm"
        style={{ background: color }}
      />
      <span className="text-xs">{label}</span>
    </div>
  );
}

function SimpleBikeSVG({ focus }: { focus: "saddle" | "frame" | "cockpit" }) {
  // Colors per section
  const seatColor = focus === "saddle" ? "#f59e0b" : "#6b7280"; // amber-500 : gray-500
  const frameColor = focus === "frame" ? "#3b82f6" : "#6b7280"; // blue-500 : gray-500
  const cockpitColor = focus === "cockpit" ? "#10b981" : "#6b7280"; // emerald-500 : gray-500
  const wheelColor = "#94a3b8"; // slate-400

  return (
    <svg
      viewBox="0 0 400 220"
      className="w-full h-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Bike diagram"
    >
      {/* Wheels */}
      <circle
        cx="80"
        cy="170"
        r="40"
        fill="none"
        stroke={wheelColor}
        strokeWidth="4"
      />
      <circle
        cx="300"
        cy="170"
        r="40"
        fill="none"
        stroke={wheelColor}
        strokeWidth="4"
      />

      {/* Frame: seat tube, top tube, down tube, chainstay, seatstay */}
      {/* Seat tube (highlight for saddle) */}
      <line
        x1="140"
        y1="165"
        x2="165"
        y2="80"
        stroke={seatColor}
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* Top tube (front end) */}
      <line
        x1="165"
        y1="80"
        x2="260"
        y2="90"
        stroke={frameColor}
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* Head tube (front end) */}
      <line
        x1="260"
        y1="90"
        x2="255"
        y2="120"
        stroke={frameColor}
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* Down tube (front end) */}
      <line
        x1="255"
        y1="120"
        x2="160"
        y2="140"
        stroke={frameColor}
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* Chainstay / seatstay (neutral) */}
      <line
        x1="140"
        y1="165"
        x2="190"
        y2="165"
        stroke="#64748b"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <line
        x1="165"
        y1="80"
        x2="220"
        y2="130"
        stroke="#64748b"
        strokeWidth="6"
        strokeLinecap="round"
      />

      {/* Cockpit: stem + bar */}
      <line
        x1="255"
        y1="100"
        x2="285"
        y2="100"
        stroke={cockpitColor}
        strokeWidth="6"
        strokeLinecap="round"
      />
      <rect x="285" y="92" width="40" height="16" rx="6" fill={cockpitColor} />

      {/* Saddle */}
      <rect x="152" y="65" width="40" height="10" rx="5" fill={seatColor} />

      {/* Crank (neutral) */}
      <circle cx="190" cy="165" r="6" fill="#64748b" />
      <line
        x1="190"
        y1="165"
        x2="205"
        y2="150"
        stroke="#64748b"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}
