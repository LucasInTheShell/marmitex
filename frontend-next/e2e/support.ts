import { expect, type Page } from "@playwright/test";

/** Credentials provisioned in the isolated E2E PostgreSQL database. */
export const ADMIN = {
  email: "admin@mavi.local",
  password: "mavi-admin-2026",
};

/** The company the critical path creates and then orders as. */
export const COMPANY = {
  name: "Acme Ltda",
  email: "acme@empresa.local",
  password: "acme-2026-senha",
};

export const DISH = {
  name: "Frango grelhado com arroz",
  description: "Arroz, feijão e salada",
};

export async function signIn(
  page: Page,
  credentials: { email: string; password: string },
) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(credentials.email);
  await page.getByLabel("Senha").fill(credentials.password);
  await page.getByRole("button", { name: "Entrar" }).click();
}

export async function signOut(page: Page) {
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
}
