"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { BikeProduct, Geometry } from "@/types";

export interface ComparisonItem {
  product: BikeProduct;
}

interface ComparisonContextType {
  comparisonList: ComparisonItem[];
  addToCompare: (product: BikeProduct) => void;
  removeFromCompare: (productId: number) => void;
  clearComparison: () => void;
  isInComparison: (productId: number) => boolean;
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
                item.product &&
                typeof item.product.id === "number" &&
                item.product.frameset &&
                typeof item.product.frameset.size_label === "string",
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

  const addToCompare = (product: BikeProduct) => {
    setComparisonList((prev) => {
      if (prev.some((item) => item.product.id === product.id)) {
        return prev;
      }
      return [...prev, { product }];
    });
  };

  const removeFromCompare = (productId: number) => {
    setComparisonList((prev) =>
      prev.filter((item) => item.product.id !== productId),
    );
  };

  const clearComparison = () => {
    setComparisonList([]);
  };

  const isInComparison = (productId: number) => {
    return comparisonList.some((item) => item?.product?.id === productId);
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
