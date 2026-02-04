"use client";

import React from "react";
import { Geometry } from "../types";

interface BikeFrameSVGProps {
  geometry: Geometry;
  className?: string;
  width?: number;
  height?: number;
  showWheels?: boolean;
}

const FRAME_COLOR = "#2563eb"; // blue-600
const WHEEL_COLOR = "#94a3b8"; // slate-400
const TIRE_COLOR = "#1e293b"; // slate-800
const FRAME_TUBE_WIDTH = 25;
const WHEEL_DIAMETER_MM = 622;
const TIRE_WIDTH_MM = 30;
const RIM_DEPTH_MM = 45;
const MARGIN_PX = 4;
const SCALE = 0.35;

export default function BikeFrameSVG({
  geometry,
  className = "",
  width,
  height,
  showWheels = false,
}: BikeFrameSVGProps) {
  // Inputs
  const {
    stack,
    reach,
    bb_drop,
    chainstay_length: chainstay,
    seat_tube_length: seatTube,
    seat_tube_angle: seatAngle,
    head_tube_length: headTube,
    head_tube_angle: headAngle,
    wheelbase,
  } = geometry;

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
  const wheelRadius = (WHEEL_DIAMETER_MM + TIRE_WIDTH_MM) / 2;
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

  const wheelR = ((WHEEL_DIAMETER_MM + TIRE_WIDTH_MM) / 2) * currentScale;
  const rimR = ((WHEEL_DIAMETER_MM - RIM_DEPTH_MM) / 2) * currentScale;
  const tireW = TIRE_WIDTH_MM * currentScale;
  const rimW = RIM_DEPTH_MM * currentScale;
  const tubeW = Math.max(FRAME_TUBE_WIDTH * currentScale, 1.5);

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
            stroke={TIRE_COLOR}
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
            stroke={TIRE_COLOR}
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
        x1={pSeatTop[0]}
        y1={pSeatTop[1]}
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
        x2={pHeadBottom[0]}
        y2={pHeadBottom[1]}
        stroke={FRAME_COLOR}
        strokeWidth={tubeW}
        strokeLinecap="round"
      />
      {/* Top Tube */}
      <line
        x1={pSeatTop[0]}
        y1={pSeatTop[1]}
        x2={pHeadTop[0]}
        y2={pHeadTop[1]}
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
        cx={pSeatTop[0]}
        cy={pSeatTop[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
      <circle
        cx={pHeadTop[0]}
        cy={pHeadTop[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
      <circle
        cx={pHeadBottom[0]}
        cy={pHeadBottom[1]}
        r={tubeW / 2}
        fill={FRAME_COLOR}
      />
    </svg>
  );
}
