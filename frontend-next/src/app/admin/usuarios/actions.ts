"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { AccountRole } from "@/lib/types";

export type AccountFormState = { error?: string; success?: string };

const ACCOUNT_ROLES: AccountRole[] = ["admin", "kitchen", "company"];

export async function createAccount(
  _state: AccountFormState,
  formData: FormData,
): Promise<AccountFormState> {
  await requireRole("admin");

  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");
  const role = String(formData.get("role") ?? "") as AccountRole;
  const companyId = String(formData.get("company_id") ?? "").trim();

  if (!name || !email || !password || !ACCOUNT_ROLES.includes(role)) {
    return { error: "Preencha nome, e-mail, senha e perfil de acesso." };
  }
  if (password.length < 8) {
    return { error: "A senha precisa ter ao menos 8 caracteres." };
  }
  if (role === "company" && !companyId) {
    return { error: "Selecione a empresa vinculada a esse usuário." };
  }

  try {
    await apiRequest("/api/v1/accounts", {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({
        name,
        email,
        password,
        role,
        company_id: role === "company" ? companyId : null,
      }),
    });
  } catch (error) {
    if (error instanceof ApiError && error.code === "email_already_exists") {
      return { error: "Já existe um usuário com esse e-mail." };
    }
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível criar o usuário.",
    };
  }

  revalidatePath("/admin/usuarios");
  return { success: `Usuário ${name} criado com sucesso.` };
}
