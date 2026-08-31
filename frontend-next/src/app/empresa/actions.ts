"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { Order, OrderCreatePayload } from "@/lib/types";

export type OrderActionResult = { error?: string; order?: Order };

function actionError(error: unknown, fallback: string): OrderActionResult {
  return { error: error instanceof ApiError ? error.message : fallback };
}

function revalidateOrderPanels() {
  revalidatePath("/empresa");
  revalidatePath("/cozinha");
  revalidatePath("/cozinha/modo-tv");
}

export async function createOrderAction(
  payload: OrderCreatePayload,
  idempotencyKey: string,
): Promise<OrderActionResult> {
  await requireRole("company");
  if (!payload.date || !payload.meal_schedule_id || payload.items.length < 1) {
    return { error: "Escolha a data, o horário e ao menos um item." };
  }

  try {
    const order = await apiRequest<Order>("/api/v1/orders", {
      method: "POST",
      token: await sessionToken(),
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    });
    revalidateOrderPanels();
    return { order };
  } catch (error) {
    return actionError(error, "Não foi possível criar o pedido.");
  }
}

export async function cancelOrderAction(
  orderId: string,
): Promise<OrderActionResult> {
  await requireRole("company");
  try {
    const order = await apiRequest<Order>(`/api/v1/orders/${orderId}/cancel`, {
      method: "POST",
      token: await sessionToken(),
      body: JSON.stringify({ reason: "Cancelado pela empresa" }),
    });
    revalidateOrderPanels();
    return { order };
  } catch (error) {
    return actionError(error, "Não foi possível cancelar o pedido.");
  }
}
