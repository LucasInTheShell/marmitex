import Link from "next/link";

import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { appTimeZone } from "@/lib/env";
import { sessionToken } from "@/lib/session";
import type { Menu, MenuItem } from "@/lib/types";
import {
  addDays,
  businessDaysOfWeek,
  mondayOfWeek,
  shortDateLabel,
  todayInTimeZone,
} from "@/lib/week";

import { WeekMenuForm } from "./form";

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export default async function WeekMenuPage({
  searchParams,
}: {
  searchParams: Promise<{ semana?: string }>;
}) {
  await requireRole("admin");

  const { semana } = await searchParams;
  const anchor =
    semana && ISO_DATE.test(semana) ? semana : todayInTimeZone(appTimeZone());
  const weekStart = mondayOfWeek(anchor);
  const days = businessDaysOfWeek(weekStart);

  const token = await sessionToken();
  const [menuItems, menus] = await Promise.all([
    apiRequest<MenuItem[]>("/api/v1/menu-items", { token }),
    apiRequest<Menu[]>(
      `/api/v1/menus?start=${encodeURIComponent(days[0])}&end=${encodeURIComponent(days[4])}`,
      { token },
    ),
  ]);

  const menusByDate: Record<string, Menu | undefined> = {};
  for (const menu of menus) menusByDate[menu.date] = menu;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-stone-800">
          Cardápio da semana
        </h1>

        <div className="flex items-center gap-3 text-sm">
          <Link
            href={`/admin/cardapio?semana=${addDays(weekStart, -7)}`}
            className="text-stone-600 underline hover:text-stone-900"
          >
            Semana anterior
          </Link>
          <span className="text-stone-500">
            {shortDateLabel(days[0])} – {shortDateLabel(days[4])}
          </span>
          <Link
            href={`/admin/cardapio?semana=${addDays(weekStart, 7)}`}
            className="text-stone-600 underline hover:text-stone-900"
          >
            Próxima semana
          </Link>
        </div>
      </div>

      <WeekMenuForm
        weekStart={weekStart}
        days={days}
        menuItems={menuItems}
        menusByDate={menusByDate}
      />
    </div>
  );
}
