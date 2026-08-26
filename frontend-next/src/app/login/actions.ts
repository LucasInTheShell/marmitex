"use server";

import { redirect } from "next/navigation";

import { ApiError, apiRequest } from "@/lib/api/client";
import { homePathFor } from "@/lib/auth";
import {
  clearSessionToken,
  sessionToken,
  setSessionToken,
} from "@/lib/session";
import type { Account } from "@/lib/types";

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

  try {
    const session = await apiRequest<{
      token: string;
      expires_at: string;
      account: Account;
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await setSessionToken(session.token, session.expires_at);
    redirect(homePathFor(session.account.role));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { error: "E-mail ou senha inválidos." };
    }
    if (error instanceof ApiError) return { error: error.message };
    throw error;
  }
}

export async function signOut() {
  const token = await sessionToken();
  if (token) {
    try {
      await apiRequest<void>("/api/v1/auth/logout", {
        method: "POST",
        token,
      });
    } catch {
      // Clearing the local cookie still signs out this browser.
    }
  }
  await clearSessionToken();
  redirect("/login");
}
