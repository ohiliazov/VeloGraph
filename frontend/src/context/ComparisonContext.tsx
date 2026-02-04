"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { Bike, Geometry } from "@/types";

export interface ComparisonItem {
  bike: Bike;
  geometry: Geometry;
}

interface ComparisonContextType {
  comparisonList: ComparisonItem[];
  addToCompare: (bike: Bike, geometry: Geometry) => void;
  removeFromCompare: (bikeId: number, sizeLabel: string) => void;
  clearComparison: () => void;
  isInComparison: (bikeId: number, sizeLabel: string) => boolean;
}

const ComparisonContext = createContext<ComparisonContextType | undefined>(
  undefined,
);

export const ComparisonProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [comparisonList, setComparisonList] = useState<ComparisonItem[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem("comparisonList");
    if (saved) {
      try {
        setComparisonList(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse comparison list", e);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("comparisonList", JSON.stringify(comparisonList));
  }, [comparisonList]);

  const addToCompare = (bike: Bike, geometry: Geometry) => {
    setComparisonList((prev) => {
      if (
        prev.some(
          (item) =>
            item.bike.id === bike.id &&
            item.geometry.size_label === geometry.size_label,
        )
      ) {
        return prev;
      }
      return [...prev, { bike, geometry }];
    });
  };

  const removeFromCompare = (bikeId: number, sizeLabel: string) => {
    setComparisonList((prev) =>
      prev.filter(
        (item) =>
          !(item.bike.id === bikeId && item.geometry.size_label === sizeLabel),
      ),
    );
  };

  const clearComparison = () => {
    setComparisonList([]);
  };

  const isInComparison = (bikeId: number, sizeLabel: string) => {
    return comparisonList.some(
      (item) =>
        item.bike.id === bikeId && item.geometry.size_label === sizeLabel,
    );
  };

  return (
    <ComparisonContext.Provider
      value={{
        comparisonList,
        addToCompare,
        removeFromCompare,
        clearComparison,
        isInComparison,
      }}
    >
      {children}
    </ComparisonContext.Provider>
  );
};

export const useComparison = () => {
  const context = useContext(ComparisonContext);
  if (context === undefined) {
    throw new Error("useComparison must be used within a ComparisonProvider");
  }
  return context;
};
