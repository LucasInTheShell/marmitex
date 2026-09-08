import { ApiError, apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { Order } from "@/lib/types";

export async function GET(
  _request: Request,
  context: { params: Promise<{ orderId: string }> },
) {
  await requireRole("company");
  const { orderId } = await context.params;
  try {
    const order = await apiRequest<Order>(`/api/v1/orders/${orderId}`, {
      token: await sessionToken(),
    });
    return Response.json(order, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 500;
    return Response.json({ error: "Não foi possível consultar o pedido." }, { status });
  }
}
