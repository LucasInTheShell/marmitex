"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import { SIZE_OPTIONS } from "@/lib/types";

export type MenuItemFormState = { error?: string; success?: string };

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MAX_IMAGES = 6;
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export async function createMenuItem(
  _state: MenuItemFormState,
  formData: FormData,
): Promise<MenuItemFormState> {
  await requireRole("admin");
  const parsed = parseMenuItemForm(formData);
  if (!parsed.ok) return parsed.state;

  try {
    await apiRequest("/api/v1/menu-items", {
      method: "POST",
      token: await sessionToken(),
      body: parsed.payload,
    });
  } catch (error) {
    return apiError(error, "Não foi possível cadastrar o prato.");
  }

  revalidateMenuPaths();
  return { success: `Prato ${parsed.name} cadastrado.` };
}

export async function updateMenuItem(
  itemId: string,
  _state: MenuItemFormState,
  formData: FormData,
): Promise<MenuItemFormState> {
  await requireRole("admin");
  const parsed = parseMenuItemForm(formData);
  if (!parsed.ok) return parsed.state;
  try {
    await apiRequest(`/api/v1/menu-items/${itemId}`, {
      method: "PUT",
      token: await sessionToken(),
      body: parsed.payload,
    });
  } catch (error) {
    return apiError(error, "Não foi possível atualizar o prato.");
  }

  revalidateMenuPaths();
  return { success: `Prato ${parsed.name} atualizado.` };
}

export async function deleteMenuItem(
  itemId: string,
  _state: MenuItemFormState,
): Promise<MenuItemFormState> {
  void _state;
  await requireRole("admin");
  try {
    await apiRequest(`/api/v1/menu-items/${itemId}`, {
      method: "DELETE",
      token: await sessionToken(),
    });
  } catch (error) {
    return apiError(error, "Não foi possível excluir o prato.");
  }

  revalidateMenuPaths();
  return { success: "Prato excluído." };
}

function parseMenuItemForm(
  formData: FormData,
):
  | { ok: true; name: string; payload: FormData }
  | { ok: false; state: MenuItemFormState } {
  const name = String(formData.get("name") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const rawPrice = String(formData.get("price") ?? "").trim();
  const sizes = formData
    .getAll("sizes")
    .map(String)
    .filter((size): size is (typeof SIZE_OPTIONS)[number] =>
      SIZE_OPTIONS.includes(size as (typeof SIZE_OPTIONS)[number]),
    );
  const images = formData
    .getAll("images")
    .filter((entry): entry is File => entry instanceof File && entry.size > 0);
  const removeImageIds = formData.getAll("remove_image_ids").map(String);
  const existingImageCount = Number(formData.get("existing_image_count") ?? 0);

  if (!name) return { ok: false, state: { error: "Informe o nome do prato." } };
  if (sizes.length === 0) {
    return { ok: false, state: { error: "Selecione ao menos um tamanho." } };
  }
  if (rawPrice && !Number.isFinite(Number(rawPrice.replace(",", ".")))) {
    return { ok: false, state: { error: "Preço inválido." } };
  }
  if (images.length > MAX_IMAGES) {
    return { ok: false, state: { error: `Selecione no máximo ${MAX_IMAGES} imagens.` } };
  }
  if (existingImageCount - removeImageIds.length + images.length > MAX_IMAGES) {
    return { ok: false, state: { error: `Um prato pode ter no máximo ${MAX_IMAGES} imagens.` } };
  }
  for (const image of images) {
    if (image.size > MAX_IMAGE_BYTES) {
      return { ok: false, state: { error: "A imagem deve ter no máximo 5 MB." } };
    }
    if (!IMAGE_TYPES.has(image.type)) {
      return { ok: false, state: { error: "Use uma imagem JPEG, PNG ou WebP." } };
    }
  }

  const payload = new FormData();
  payload.set("name", name);
  payload.set("description", description);
  if (rawPrice) payload.set("price", rawPrice.replace(",", "."));
  for (const size of sizes) payload.append("size_options", size);
  for (const image of images) payload.append("images", image);
  for (const imageId of removeImageIds) payload.append("remove_image_ids", imageId);
  const primaryImageId = String(formData.get("primary_image_id") ?? "");
  const primaryNewImageIndex = String(formData.get("primary_new_image_index") ?? "");
  if (primaryImageId) payload.set("primary_image_id", primaryImageId);
  if (primaryNewImageIndex) {
    payload.set("primary_new_image_index", primaryNewImageIndex);
  }
  return { ok: true, name, payload };
}

function apiError(error: unknown, fallback: string): MenuItemFormState {
  return { error: error instanceof ApiError ? error.message : fallback };
}

function revalidateMenuPaths() {
  revalidatePath("/admin/pratos");
  revalidatePath("/admin/cardapio");
  revalidatePath("/empresa");
}
