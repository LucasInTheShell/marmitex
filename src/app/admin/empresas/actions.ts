"use server";

import { revalidatePath } from "next/cache";

import { requireRole } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

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

  const supabase = await createClient();
  const { data: company, error: companyError } = await supabase
    .from("companies")
    .insert({ name })
    .select("id")
    .single();

  if (companyError || !company) {
    return { error: "Não foi possível criar a empresa." };
  }

  const admin = createAdminClient();
  const { data: created, error: authError } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });

  if (authError || !created.user) {
    // Roll back so the company does not linger without a way to sign in.
    await supabase.from("companies").delete().eq("id", company.id);
    return {
      error:
        authError?.message === "User already registered"
          ? "Já existe um acesso com esse e-mail."
          : "Não foi possível criar o acesso da empresa.",
    };
  }

  const { error: accountError } = await supabase.from("accounts").insert({
    id: created.user.id,
    name,
    email,
    company_id: company.id,
    role: "company",
  });

  if (accountError) {
    await admin.auth.admin.deleteUser(created.user.id);
    await supabase.from("companies").delete().eq("id", company.id);
    return { error: "Não foi possível vincular o acesso à empresa." };
  }

  revalidatePath("/admin/empresas");
  return { success: `Empresa ${name} cadastrada.` };
}
