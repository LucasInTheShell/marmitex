import { ApiError, apiRequest } from "@/lib/api/client";
import { employeeSessionToken } from "@/lib/employee-session";
import type { Order } from "@/lib/types";

export async function GET(
  _request: Request,
  context: { params: Promise<{ orderId: string }> },
) {
  const token = await employeeSessionToken();
  if (!token) return Response.json({ error: "Acesso expirado." }, { status: 401 });
  const { orderId } = await context.params;
  try {
    const order = await apiRequest<Order>(`/api/v1/employee/orders/${orderId}`, {
      token,
    });
    return Response.json(order, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 500;
    return Response.json({ error: "Não foi possível consultar o pedido." }, { status });
  }
}
