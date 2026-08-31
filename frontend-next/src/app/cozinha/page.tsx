import { KitchenPanel } from "@/app/cozinha/panel";
import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { appTimeZone } from "@/lib/env";
import { sessionToken } from "@/lib/session";
import type { DailyProductionSummary, KitchenOrder } from "@/lib/types";
import { addDays, todayInTimeZone } from "@/lib/week";

export default async function KitchenPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  await requireRole("kitchen");
  const token = await sessionToken();
  const today = todayInTimeZone(appTimeZone());
  const tomorrow = addDays(today, 1);
  const requestedDate = (await searchParams).date;
  const selectedDate = /^\d{4}-\d{2}-\d{2}$/.test(requestedDate ?? "")
    ? requestedDate!
    : today;
  const encodedDate = encodeURIComponent(selectedDate);
  const [orders, summary] = await Promise.all([
    apiRequest<KitchenOrder[]>(
      `/api/v1/kitchen/production-board?date=${encodedDate}`,
      { token },
    ),
    apiRequest<DailyProductionSummary>(
      `/api/v1/kitchen/production-summary?date=${encodedDate}`,
      { token },
    ),
  ]);

  return (
    <KitchenPanel
      selectedDate={selectedDate}
      today={today}
      tomorrow={tomorrow}
      initialOrders={orders}
      summary={summary}
    />
  );
}
