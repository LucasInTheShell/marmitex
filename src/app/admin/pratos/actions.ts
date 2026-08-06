"use server";

import { revalidatePath } from "next/cache";

import { requireRole } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { SIZE_OPTIONS } from "@/lib/types";

export type MenuItemFormState = { error?: string; success?: string };

export async function createMenuItem(
  _state: MenuItemFormState,
  formData: FormData,
): Promise<MenuItemFormState> {
  await requireRole("admin");

  const name = String(formData.get("name") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const rawPrice = String(formData.get("price") ?? "").trim();
  const sizes = formData
    .getAll("sizes")
    .map(String)
    .filter((size): size is (typeof SIZE_OPTIONS)[number] =>
      SIZE_OPTIONS.includes(size as (typeof SIZE_OPTIONS)[number]),
    );

  if (!name) return { error: "Informe o nome do prato." };
  if (sizes.length === 0) return { error: "Selecione ao menos um tamanho." };

  const price = rawPrice ? Number(rawPrice.replace(",", ".")) : null;
  if (price !== null && !Number.isFinite(price)) {
    return { error: "Preço inválido." };
  }

  const supabase = await createClient();
  const { error } = await supabase.from("menu_items").insert({
    name,
    description: description || null,
    size_options: sizes,
    price,
  });

  if (error) return { error: "Não foi possível cadastrar o prato." };

  revalidatePath("/admin/pratos");
  revalidatePath("/admin/cardapio");
  return { success: `Prato ${name} cadastrado.` };
}
