"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";

export type CompanyFormState = { error?: string; success?: string };
export type MealScheduleFormState = { error?: string; success?: string };

function weekdaysFrom(formData: FormData, field: string): number[] {
  return formData
    .getAll(field)
    .map(Number)
    .filter((day) => Number.isInteger(day) && day >= 1 && day <= 7);
}

/**
 * Creates a company together with the shared credential its employees use.
 * There is no per-employee account in v1 (CLAUDE.md §2), so this credential is
 * the company's only way in.
 */
export async function createCompany(
  _state: CompanyFormState,
  formData: FormData,
): Promise<CompanyFormState> {
  await requireRole("admin");

  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");
  const labels = formData.getAll("schedule_label").map(String);
  const times = formData.getAll("schedule_time").map(String);

  if (!name || !email || !password) {
    return { error: "Preencha nome, e-mail e senha de acesso." };
  }
  if (password.length < 8) {
    return { error: "A senha de acesso precisa ter ao menos 8 caracteres." };
  }

  const mealSchedules = labels.map((label, index) => ({
    label: label.trim(),
    meal_time: times[index] ?? "",
    weekdays: weekdaysFrom(formData, `schedule_weekdays_${index}`),
    sort_order: index,
  }));
  if (
    mealSchedules.length === 0 ||
    mealSchedules.some(
      (schedule) =>
        !schedule.label ||
        !schedule.meal_time ||
        schedule.weekdays.length === 0,
    )
  ) {
    return { error: "Configure nome, hora e dias de cada horário de refeição." };
  }

  try {
    await apiRequest("/api/v1/companies", {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({
        name,
        email,
        password,
        meal_schedules: mealSchedules,
      }),
    });
  } catch (error) {
    if (error instanceof ApiError && error.code === "email_already_exists") {
      return { error: "Já existe um acesso com esse e-mail." };
    }
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível criar a empresa.",
    };
  }

  revalidatePath("/admin/empresas");
  return { success: `Empresa ${name} cadastrada.` };
}

export async function addMealSchedule(
  companyId: string,
  _state: MealScheduleFormState,
  formData: FormData,
): Promise<MealScheduleFormState> {
  await requireRole("admin");

  const label = String(formData.get("label") ?? "").trim();
  const mealTime = String(formData.get("meal_time") ?? "");
  const weekdays = weekdaysFrom(formData, "weekdays");
  if (!label || !mealTime || weekdays.length === 0) {
    return { error: "Informe nome, hora e ao menos um dia da semana." };
  }

  try {
    await apiRequest(`/api/v1/companies/${companyId}/meal-schedules`, {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({ label, meal_time: mealTime, weekdays }),
    });
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível adicionar o horário.",
    };
  }

  revalidatePath("/admin/empresas");
  revalidatePath("/empresa");
  return { success: "Horário adicionado." };
}

export async function updateMealSchedule(
  companyId: string,
  scheduleId: string,
  _state: MealScheduleFormState,
  formData: FormData,
): Promise<MealScheduleFormState> {
  await requireRole("admin");

  const label = String(formData.get("label") ?? "").trim();
  const mealTime = String(formData.get("meal_time") ?? "");
  const weekdays = weekdaysFrom(formData, "weekdays");
  if (!label || !mealTime || weekdays.length === 0) {
    return { error: "Informe nome, hora e ao menos um dia da semana." };
  }

  try {
    await apiRequest(
      `/api/v1/companies/${companyId}/meal-schedules/${scheduleId}`,
      {
        method: "PATCH",
        token: await sessionToken(),
        body: JSON.stringify({
          label,
          meal_time: mealTime,
          weekdays,
          active: formData.get("active") === "on",
        }),
      },
    );
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível atualizar o horário.",
    };
  }

  revalidatePath("/admin/empresas");
  revalidatePath("/empresa");
  return { success: "Horário atualizado." };
}
