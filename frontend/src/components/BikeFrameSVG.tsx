"use client";

import React from "react";
import { GeometrySpec } from "@/types";

interface BikeFrameSVGProps {
  geometry: GeometrySpec;
  wheelSize?: string;
  maxTireWidth?: string;
  className?: string;
  width?: number;
  height?: number;
  showWheels?: boolean;
  frameColor?: string | null;
  jointAdjustments?: {
    topToSeatDrop?: number;
    topToHeadDrop?: number;
    downToHeadRise?: number;
  };
}

const DEFAULT_JOINTS = {
  topToSeatDrop: 0.08,
  topToHeadDrop: 0.07,
  downToHeadRise: 0.1,
};

const DEFAULT_FRAME_COLOR = "#2563eb"; // blue-600
const WHEEL_COLOR = "#94a3b8"; // slate-400
const FRAME_TUBE_WIDTH = 25;
const DEFAULT_WHEEL_DIAMETER_MM = 622;
const DEFAULT_TIRE_WIDTH_MM = 30;
const RIM_DEPTH_MM = 30;
const MARGIN_PX = 10;
const SCALE = 0.35;

const WHEEL_SIZE_MAP: Record<string, number> = {
  "700": 622,
  "584": 584,
  "559": 559,
  "507": 507,
  "406": 406,
  "305": 305,
  "254": 254,
  "203": 203,
  // Defensive inch-based keys
  "29": 622,
  "28": 622,
  "27.5": 584,
  "26": 559,
  "24": 507,
  "20": 406,
  "16": 305,
  "14": 254,
  "12": 203,
};

function normalizeColor(input?: string | null): string | null {
  if (!input) return null;
  const s = String(input).trim();
  // 1) Hex code in the text
  const hex = s.match(/#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})/);
  if (hex) return hex[0];

  const lower = s.toLowerCase();
  // 2) Basic mapping for common EN/PL color words
  const map: Record<string, string> = {
    black: "#000000",
    czarny: "#000000",
    white: "#ffffff",
    biały: "#ffffff",
    bialy: "#ffffff",
    red: "#ef4444",
    czerwony: "#ef4444",
    blue: "#3b82f6",
    niebieski: "#3b82f6",
    green: "#22c55e",
    zielony: "#22c55e",
    gray: "#6b7280",
    grey: "#6b7280",
    szary: "#6b7280",
    graphite: "#4b5563",
    grafitowy: "#4b5563",
    silver: "#9ca3af",
    srebrny: "#9ca3af",
    gold: "#eab308",
    złoty: "#eab308",
    zolty: "#eab308",
    orange: "#f97316",
    pomarańczowy: "#f97316",
    pomaranczowy: "#f97316",
    yellow: "#facc15",
    purple: "#a855f7",
    fioletowy: "#a855f7",
    pink: "#ec4899",
    różowy: "#ec4899",
    rozowy: "#ec4899",
    brown: "#92400e",
    brązowy: "#92400e",
    brazowy: "#92400e",
    beige: "#f5f5dc",
    navy: "#1e3a8a",
    granatowy: "#1e3a8a",
    turquoise: "#14b8a6",
    turkusowy: "#14b8a6",
    teal: "#0d9488",
  };

  // Try token-wise
  const tokens = lower.split(/[\s,\/\-]+/);
  for (const tok of tokens) {
    if (map[tok]) return map[tok];
  }
  // Last resort: return the raw string and let the browser try
  return s;
}

export default function BikeFrameSVG({
  geometry,
  wheelSize,
  maxTireWidth,
  className = "",
  width,
  height,
  showWheels = true,
  frameColor,
  jointAdjustments,
}: BikeFrameSVGProps) {
  // Inputs
  const {
    stack_mm: stack,
    reach_mm: reach,
    bb_drop_mm: bb_drop,
    chainstay_length_mm: chainstay,
    seat_tube_length_mm: seatTubeRaw,
    seat_tube_angle: seatAngle,
    head_tube_length_mm: headTubeRaw,
    head_tube_angle: headAngle,
    wheelbase_mm: wheelbase,
  } = geometry;

  const seatTube = seatTubeRaw || 500;
  const headTube = headTubeRaw || 150;

  // Wheel and Tire dimensions
  const wheelDiameter =
    (wheelSize && WHEEL_SIZE_MAP[wheelSize]) || DEFAULT_WHEEL_DIAMETER_MM;
  const tireWidth = maxTireWidth
    ? parseFloat(maxTireWidth)
    : DEFAULT_TIRE_WIDTH_MM;

  // Compute points (relative to BB at 0,0)
  // Note: Y is positive upwards in math, but positive downwards in SVG.
  // We'll calculate in "math" coordinates first, then transform.
  const headTop = [reach, stack - bb_drop];
  const headBottom = [
    headTop[0] + headTube * Math.cos((headAngle * Math.PI) / 180),
    headTop[1] - headTube * Math.sin((headAngle * Math.PI) / 180),
  ];

  const points = {
    bb: [0, -bb_drop],
    rear_axle: [-chainstay, 0],
    front_axle: [wheelbase - chainstay, 0],
    seat_top: [
      -seatTube * Math.cos((seatAngle * Math.PI) / 180),
      seatTube * Math.sin((seatAngle * Math.PI) / 180) - bb_drop,
    ],
    head_top: headTop,
    head_bottom: headBottom,
  };

  // Canvas calculation
  const wheelRadius = (wheelDiameter + tireWidth) / 2;
  const xs = [
    points.rear_axle[0] - (showWheels ? wheelRadius : 0),
    points.front_axle[0] + (showWheels ? wheelRadius : 0),
    points.seat_top[0],
    points.head_top[0],
    points.head_bottom[0],
    points.bb[0],
  ];
  const ys = [
    points.rear_axle[1] - (showWheels ? wheelRadius : 0),
    points.rear_axle[1] + (showWheels ? wheelRadius : 0),
    points.seat_top[1],
    points.head_top[1],
    points.head_bottom[1],
    points.bb[1],
    0, // axle line
  ];

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const widthMM = Math.max(maxX - minX, 1);
  const heightMM = Math.max(maxY - minY, 1);

  // Dynamic scale to fit requested dimensions if provided
  let currentScale = SCALE;
  const availableW = width ? width - 2 * MARGIN_PX : 0;
  const availableH = height ? height - 2 * MARGIN_PX : 0;

  if (width && height) {
    currentScale = Math.min(availableW / widthMM, availableH / heightMM);
  } else if (width) {
    currentScale = availableW / widthMM;
  } else if (height) {
    currentScale = availableH / heightMM;
  }

  // Ensure scale is not zero or negative
  currentScale = Math.max(currentScale, 0.01);

  const svgW = width || widthMM * currentScale + 2 * MARGIN_PX;
  const svgH = height || heightMM * currentScale + 2 * MARGIN_PX;

  // Transformations
  // tx, ty are where the math (0,0) should be in SVG pixels
  // Center the drawing in the box
  const offsetX = (svgW - widthMM * currentScale - 2 * MARGIN_PX) / 2;
  const offsetY = (svgH - heightMM * currentScale - 2 * MARGIN_PX) / 2;

  const tx = MARGIN_PX + offsetX - minX * currentScale;
  const ty = MARGIN_PX + offsetY + maxY * currentScale;

  // Convert point to SVG space
  const p = (pt: number[]) => [
    tx + pt[0] * currentScale,
    ty - pt[1] * currentScale,
  ];

  const pBB = p(points.bb);
  const pRear = p(points.rear_axle);
  const pFront = p(points.front_axle);
  const pSeatTop = p(points.seat_top);
  const pHeadTop = p(points.head_top);
  const pHeadBottom = p(points.head_bottom);

  // Joint adjustments
  const J = { ...DEFAULT_JOINTS, ...jointAdjustments };
  const sub = (a: number[], b: number[]) => [a[0] - b[0], a[1] - b[1]];
  const add = (a: number[], b: number[]) => [a[0] + b[0], a[1] + b[1]];
  const mul = (v: number[], s: number) => [v[0] * s, v[1] * s];
  const norm = (v: number[]) => {
    const L = Math.hypot(v[0], v[1]) || 1;
    return [v[0] / L, v[1] / L];
  };

  const uSeat = norm(sub(points.seat_top, points.bb));
  const uHead = norm(sub(points.head_top, points.head_bottom));

  const seatJoint = add(
    points.seat_top,
    mul(uSeat, -J.topToSeatDrop * seatTube),
  );
  const headTopJoint = add(
    points.head_top,
    mul(uHead, -J.topToHeadDrop * headTube),
  );
  const headBottomJoint = add(
    points.head_bottom,
    mul(uHead, J.downToHeadRise * headTube),
  );

  const pSeatJoint = p(seatJoint);
  const pHeadTopJoint = p(headTopJoint);
  const pHeadBottomJoint = p(headBottomJoint);

  const wheelR = ((wheelDiameter + tireWidth) / 2) * currentScale;
  const rimR = ((wheelDiameter - RIM_DEPTH_MM) / 2) * currentScale;
  const tireW = tireWidth * currentScale;
  const rimW = RIM_DEPTH_MM * currentScale;
  const tubeW = Math.max(FRAME_TUBE_WIDTH * currentScale, 1.5);

  const FRAME_COLOR = normalizeColor(frameColor) || DEFAULT_FRAME_COLOR;

  return (
    <svg
      viewBox={`0 0 ${svgW} ${svgH}`}
      width={width}
      height={height}
      className={className}
    >
      {/* Wheels */}
      {showWheels && (
        <>
          <circle
            cx={pRear[0]}
            cy={pRear[1]}
            r={wheelR}
            className="stroke-[#1e293b] dark:stroke-[#94a3b8]"
            strokeWidth={tireW}
            fill="none"
          />
          <circle
            cx={pRear[0]}
            cy={pRear[1]}
            r={rimR}
            stroke={WHEEL_COLOR}
            strokeWidth={rimW}
            fill="none"
          />
          <circle
            cx={pFront[0]}
            cy={pFront[1]}
            r={wheelR}
            className="stroke-[#1e293b] dark:stroke-[#94a3b8]"
            strokeWidth={tireW}
            fill="none"
          />
          <circle
            cx={pFront[0]}
            cy={pFront[1]}
            r={rimR}
            stroke={WHEEL_COLOR}
            strokeWidth={rimW}
            fill="none"
          />
        </>
      )}

      {/* Frame Tubes */}
      {/* Chainstay */}
      <line
        x1={pBB[0]}
        y1={pBB[1]}
        x2={pRear[0]}
        y2={pRear[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Seat Tube */}
      <line
        x1={pBB[0]}
        y1={pBB[1]}
        x2={pSeatTop[0]}
        y2={pSeatTop[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Seat Stay */}
      <line
        x1={pSeatJoint[0]}
        y1={pSeatJoint[1]}
        x2={pRear[0]}
        y2={pRear[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Down Tube */}
      <line
        x1={pBB[0]}
        y1={pBB[1]}
        x2={pHeadBottomJoint[0]}
        y2={pHeadBottomJoint[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Top Tube */}
      <line
        x1={pSeatJoint[0]}
        y1={pSeatJoint[1]}
        x2={pHeadTopJoint[0]}
        y2={pHeadTopJoint[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Head Tube */}
      <line
        x1={pHeadBottom[0]}
        y1={pHeadBottom[1]}
        x2={pHeadTop[0]}
        y2={pHeadTop[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Fork (Simplified) */}
      <line
        x1={pHeadBottom[0]}
        y1={pHeadBottom[1]}
        x2={pFront[0]}
        y2={pFront[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />

      {/* Joints */}
      <circle cx={pBB[0]} cy={pBB[1]} r={tubeW / 2} fill={FRAME_COLOR} />
      <circle
        cx={pSeatJoint[0]}
        cy={pSeatJoint[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
      <circle
        cx={pHeadTopJoint[0]}
        cy={pHeadTopJoint[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
      <circle
        cx={pHeadBottomJoint[0]}
        cy={pHeadBottomJoint[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
    </svg>
  );
}
