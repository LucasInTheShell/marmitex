"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";

export type OperationalSettingsFormState = {
  error?: string;
  success?: string;
};

export async function updateOperationalSettings(
  _state: OperationalSettingsFormState,
  formData: FormData,
): Promise<OperationalSettingsFormState> {
  await requireRole("admin");

  const minutes = Number(formData.get("order_cutoff_lead_minutes"));
  if (!Number.isInteger(minutes) || minutes < 0 || minutes > 1440) {
    return { error: "Informe uma antecedência entre 0 e 1440 minutos." };
  }

  try {
    await apiRequest("/api/v1/operational-settings", {
      method: "PUT",
      token: await sessionToken(),
      body: JSON.stringify({ order_cutoff_lead_minutes: minutes }),
    });
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível atualizar a configuração.",
    };
  }

  revalidatePath("/admin/configuracoes");
  revalidatePath("/empresa");
  return { success: "Antecedência dos pedidos atualizada." };
}
