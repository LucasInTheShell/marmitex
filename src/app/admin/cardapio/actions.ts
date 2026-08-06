"use server";

import { revalidatePath } from "next/cache";

import { requireRole } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { businessDaysOfWeek } from "@/lib/week";

export type MenuFormState = { error?: string; success?: string };

/** Reads the checkbox group named `dia-<date>` for each business day. */
function selectionsFrom(formData: FormData, days: string[]) {
  return days.map((date) => ({
    date,
    menu_item_ids: formData.getAll(`dia-${date}`).map(String),
  }));
}

export async function saveWeekMenu(
  _state: MenuFormState,
  formData: FormData,
): Promise<MenuFormState> {
  await requireRole("admin");

  const weekStart = String(formData.get("weekStart") ?? "");
  if (!weekStart) return { error: "Semana inválida." };

  const days = businessDaysOfWeek(weekStart);
  const supabase = await createClient();

  for (const { date, menu_item_ids } of selectionsFrom(formData, days)) {
    const { error } = await supabase
      .from("menus")
      .upsert({ date, menu_item_ids }, { onConflict: "date" });

    if (error) return { error: "Não foi possível salvar o cardápio." };
  }

  revalidatePath("/admin/cardapio");
  return { success: "Cardápio salvo." };
}

/**
 * Publishes every day of the week that has at least one dish. Publishing is
 * what makes the menu visible to the companies (CLAUDE.md §7.4).
 */
export async function publishWeekMenu(
  _state: MenuFormState,
  formData: FormData,
): Promise<MenuFormState> {
  await requireRole("admin");

  const weekStart = String(formData.get("weekStart") ?? "");
  if (!weekStart) return { error: "Semana inválida." };

  const days = businessDaysOfWeek(weekStart);
  const supabase = await createClient();

  const { data: menus, error: readError } = await supabase
    .from("menus")
    .select("date, menu_item_ids")
    .in("date", days)
    .returns<{ date: string; menu_item_ids: string[] }[]>();

  if (readError) return { error: "Não foi possível ler o cardápio." };

  const publishable = (menus ?? [])
    .filter((menu) => menu.menu_item_ids.length > 0)
    .map((menu) => menu.date);

  if (publishable.length === 0) {
    return { error: "Adicione ao menos um prato antes de publicar." };
  }

  const { error } = await supabase
    .from("menus")
    .update({ published: true })
    .in("date", publishable);

  if (error) return { error: "Não foi possível publicar o cardápio." };

  revalidatePath("/admin/cardapio");
  return { success: "Cardápio publicado." };
}
