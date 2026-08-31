"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { KitchenOrder, KitchenProductionStatus } from "@/lib/types";

export type KitchenActionResult = { error?: string; order?: KitchenOrder };

export async function updateOrderStatusAction(
  orderId: string,
  productionStatus: KitchenProductionStatus,
): Promise<KitchenActionResult> {
  await requireRole("kitchen");
  try {
    const order = await apiRequest<KitchenOrder>(
      `/api/v1/orders/${orderId}/status`,
      {
        method: "PATCH",
        token: await sessionToken(),
        body: JSON.stringify({ production_status: productionStatus }),
      },
    );
    revalidatePath("/cozinha");
    revalidatePath("/cozinha/modo-tv");
    revalidatePath("/empresa");
    return { order };
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível atualizar o pedido.",
    };
  }
}
