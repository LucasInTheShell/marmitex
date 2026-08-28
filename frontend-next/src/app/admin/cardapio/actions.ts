"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
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
  try {
    await apiRequest("/api/v1/menus/week", {
      method: "PUT",
      token: await sessionToken(),
      body: JSON.stringify({ menus: selectionsFrom(formData, days) }),
    });
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível salvar o cardápio.",
    };
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
  try {
    await apiRequest("/api/v1/menus/week/publish", {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({ dates: days }),
    });
  } catch (error) {
    if (error instanceof ApiError && error.code === "empty_menu") {
      return { error: "Adicione ao menos um prato antes de publicar." };
    }
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível publicar o cardápio.",
    };
  }

  revalidatePath("/admin/cardapio");
  return { success: "Cardápio publicado." };
}
