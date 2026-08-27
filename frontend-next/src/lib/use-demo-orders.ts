"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createDemoOrders,
  type DemoOrder,
} from "@/lib/demo-orders";
import type { ProductionStatus } from "@/lib/types";

const STORAGE_KEY = "mavi-connect-demo-orders-v1";

function readStoredOrders(): DemoOrder[] | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored ? (JSON.parse(stored) as DemoOrder[]) : null;
  } catch {
    return null;
  }
}

function storeOrders(orders: DemoOrder[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(orders));
}

export function useDemoOrders(currentCompany?: { id: string; name: string }) {
  const companyId = currentCompany?.id;
  const companyName = currentCompany?.name;
  const [orders, setOrders] = useState<DemoOrder[]>(() =>
    createDemoOrders(currentCompany),
  );

  useEffect(() => {
    const hydration = window.setTimeout(() => {
      const company =
        companyId && companyName ? { id: companyId, name: companyName } : undefined;
      const stored = readStoredOrders();
      let nextOrders = stored ?? createDemoOrders(company);

      if (
        company &&
        !nextOrders.some((order) => order.companyId === company.id)
      ) {
        const companyOrders = createDemoOrders(company).filter(
          (order) => order.companyId === company.id,
        );
        nextOrders = [...companyOrders, ...nextOrders];
      }

      setOrders(nextOrders);
      storeOrders(nextOrders);
    }, 0);

    return () => window.clearTimeout(hydration);
  }, [companyId, companyName]);

  useEffect(() => {
    function syncOrders(event: StorageEvent) {
      if (event.key !== STORAGE_KEY || !event.newValue) return;
      try {
        setOrders(JSON.parse(event.newValue) as DemoOrder[]);
      } catch {
        // Ignore invalid data left by an older development build.
      }
    }

    window.addEventListener("storage", syncOrders);
    return () => window.removeEventListener("storage", syncOrders);
  }, []);

  const updateOrders = useCallback(
    (updater: (current: DemoOrder[]) => DemoOrder[]) => {
      setOrders((current) => {
        const updated = updater(current);
        storeOrders(updated);
        return updated;
      });
    },
    [],
  );

  const addOrder = useCallback(
    (order: DemoOrder) => updateOrders((current) => [order, ...current]),
    [updateOrders],
  );

  const setOrderStatus = useCallback(
    (orderId: string, status: ProductionStatus) =>
      updateOrders((current) =>
        current.map((order) =>
          order.id === orderId
            ? { ...order, productionStatus: status }
            : order,
        ),
      ),
    [updateOrders],
  );

  return { orders, addOrder, setOrderStatus };
}
