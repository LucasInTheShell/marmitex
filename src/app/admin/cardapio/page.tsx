import Link from "next/link";

import { requireRole } from "@/lib/auth";
import { appTimeZone } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";
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

  const supabase = await createClient();
  const [{ data: menuItems }, { data: menus }] = await Promise.all([
    supabase
      .from("menu_items")
      .select("id, name, description, size_options, price")
      .order("name")
      .returns<MenuItem[]>(),
    supabase
      .from("menus")
      .select("id, date, menu_item_ids, published")
      .in("date", days)
      .returns<Menu[]>(),
  ]);

  const menusByDate: Record<string, Menu | undefined> = {};
  for (const menu of menus ?? []) menusByDate[menu.date] = menu;

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
        menuItems={menuItems ?? []}
        menusByDate={menusByDate}
      />
    </div>
  );
}
