"use server";

import { redirect } from "next/navigation";

import { homePathFor } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import type { AccountRole } from "@/lib/types";

export type LoginState = { error?: string };

export async function signIn(
  _state: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    return { error: "Informe e-mail e senha." };
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error || !data.user) {
    return { error: "E-mail ou senha inválidos." };
  }

  const { data: account } = await supabase
    .from("accounts")
    .select("role")
    .eq("id", data.user.id)
    .single<{ role: AccountRole }>();

  if (!account) {
    await supabase.auth.signOut();
    return { error: "Esta conta não está habilitada no sistema." };
  }

  redirect(homePathFor(account.role));
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
