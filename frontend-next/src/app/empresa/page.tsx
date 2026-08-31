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

export default async function CompanyPage() {
  await requireRole("company");
  const token = await sessionToken();
  const start = todayInTimeZone(appTimeZone());
  const end = addDays(start, 13);
  const orderStart = addDays(start, -14);
  const [company, settings, availableMenus, orders] = await Promise.all([
    apiRequest<CompanyWithAccess>("/api/v1/companies/me", { token }),
    apiRequest<OperationalSettings>("/api/v1/operational-settings", { token }),
    apiRequest<AvailableMenu[]>(
      `/api/v1/menus/available?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      { token },
    ),
    apiRequest<Order[]>(
      `/api/v1/orders?start=${encodeURIComponent(orderStart)}&end=${encodeURIComponent(end)}`,
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
    />
  );
}
