"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";

export type CompanyFormState = { error?: string; success?: string };

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

  if (!name || !email || !password) {
    return { error: "Preencha nome, e-mail e senha de acesso." };
  }
  if (password.length < 8) {
    return { error: "A senha de acesso precisa ter ao menos 8 caracteres." };
  }

  try {
    await apiRequest("/api/v1/companies", {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({ name, email, password }),
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
