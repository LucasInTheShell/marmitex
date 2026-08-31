import { KitchenTvDashboard } from "@/components/kitchen-tv-dashboard";
import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { appTimeZone } from "@/lib/env";
import { sessionToken } from "@/lib/session";
import type { KitchenOrder } from "@/lib/types";
import { todayInTimeZone } from "@/lib/week";

export default async function KitchenTvPage() {
  await requireRole("kitchen");
  const today = todayInTimeZone(appTimeZone());
  const orders = await apiRequest<KitchenOrder[]>(
    `/api/v1/kitchen/production-board?date=${encodeURIComponent(today)}`,
    { token: await sessionToken() },
  );
  return <KitchenTvDashboard initialOrders={orders} date={today} />;
}
