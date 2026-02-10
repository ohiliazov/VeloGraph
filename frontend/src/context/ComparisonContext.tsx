"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { GeometrySpec } from "@/types";

export interface ComparisonItem {
  geometry: GeometrySpec;
}

interface ComparisonContextType {
  comparisonList: ComparisonItem[];
  addToCompare: (geometry: GeometrySpec) => void;
  removeFromCompare: (geometryId: number) => void;
  clearComparison: () => void;
  isInComparison: (geometryId: number) => boolean;
}

const ComparisonContext = createContext<ComparisonContextType | undefined>(
  undefined,
);

export const ComparisonProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [comparisonList, setComparisonList] = useState<ComparisonItem[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("comparisonList");
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            // Basic validation to ensure data matches new schema
            const validated = parsed.filter(
              (item) =>
                item &&
                typeof item === "object" &&
                item.geometry &&
                typeof item.geometry.id === "number" &&
                typeof item.geometry.size_label === "string",
            );
            setComparisonList(validated);
          }
        } catch (e) {
          console.error("Failed to parse comparison list", e);
        }
      }
      setIsInitialized(true);
    }
  }, []);

  useEffect(() => {
    if (isInitialized && typeof window !== "undefined") {
      localStorage.setItem("comparisonList", JSON.stringify(comparisonList));
    }
  }, [comparisonList, isInitialized]);

  const addToCompare = (geometry: GeometrySpec) => {
    setComparisonList((prev) => {
      if (prev.some((item) => item.geometry.id === geometry.id)) {
        return prev;
      }
      return [...prev, { geometry }];
    });
  };

  const removeFromCompare = (geometryId: number) => {
    setComparisonList((prev) =>
      prev.filter((item) => item.geometry.id !== geometryId),
    );
  };

  const clearComparison = () => {
    setComparisonList([]);
  };

  const isInComparison = (geometryId: number) => {
    return comparisonList.some((item) => item?.geometry?.id === geometryId);
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
