import { CompanyPanel } from "@/app/empresa/panel";
import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { appTimeZone } from "@/lib/env";
import { sessionToken } from "@/lib/session";
import type {
  AvailableMenu,
  CompanyWithAccess,
  OperationalSettings,
  Order,
} from "@/lib/types";
import { addDays, todayInTimeZone } from "@/lib/week";

function historyRange(
  today: string,
  params: { start?: string; end?: string },
): { start: string; end: string } {
  const fallback = { start: addDays(today, -14), end: addDays(today, 13) };
  const isoDate = /^\d{4}-\d{2}-\d{2}$/;
  if (!params.start || !params.end || !isoDate.test(params.start) || !isoDate.test(params.end)) {
    return fallback;
  }
  const days = (Date.parse(`${params.end}T12:00:00Z`) - Date.parse(`${params.start}T12:00:00Z`)) / 86_400_000;
  return days >= 0 && days <= 30 ? { start: params.start, end: params.end } : fallback;
}

export default async function CompanyPage({
  searchParams,
}: {
  searchParams: Promise<{ start?: string; end?: string }>;
}) {
  await requireRole("company");
  const token = await sessionToken();
  const start = todayInTimeZone(appTimeZone());
  const end = addDays(start, 13);
  const history = historyRange(start, await searchParams);
  const [company, settings, availableMenus, orders] = await Promise.all([
    apiRequest<CompanyWithAccess>("/api/v1/companies/me", { token }),
    apiRequest<OperationalSettings>("/api/v1/operational-settings", { token }),
    apiRequest<AvailableMenu[]>(
      `/api/v1/menus/available?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      { token },
    ),
    apiRequest<Order[]>(
      `/api/v1/orders?start=${encodeURIComponent(history.start)}&end=${encodeURIComponent(history.end)}`,
      { token },
    ),
  ]);

  return (
    <CompanyPanel
      company={{ id: company.id, name: company.name }}
      mealSchedules={company.meal_schedules}
      cutoffLeadMinutes={settings.order_cutoff_lead_minutes}
      availableMenus={availableMenus}
      initialOrders={orders}
      historyStart={history.start}
      historyEnd={history.end}
    />
  );
}
