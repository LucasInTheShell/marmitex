"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, apiRequest } from "@/lib/api/client";
import {
  clearEmployeeSessionToken,
  employeeSessionToken,
  setEmployeeSessionToken,
} from "@/lib/employee-session";
import type {
  EmployeeAccess,
  EmployeeOrderCreatePayload,
  Order,
  PixCheckout,
} from "@/lib/types";

export type EmployeeActionResult = { error?: string; order?: Order };
export type EmployeePixActionResult = { error?: string; checkout?: PixCheckout };

function cpfDigits(value: string): string {
  return value.replaceAll(/\D/g, "");
}

export async function accessEmployee(cpf: string): Promise<EmployeeActionResult> {
  const normalized = cpfDigits(cpf);
  if (normalized.length !== 11) {
    return { error: "Informe um CPF com 11 dígitos." };
  }
  try {
    const access = await apiRequest<EmployeeAccess>("/api/v1/employee/access", {
      method: "POST",
      body: JSON.stringify({ cpf: normalized }),
    });
    await setEmployeeSessionToken(access.token, access.expires_at);
    return {};
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível validar o CPF agora.",
    };
  }
}

export async function createEmployeeOrderAction(
  payload: EmployeeOrderCreatePayload,
  idempotencyKey: string,
): Promise<EmployeeActionResult> {
  const token = await employeeSessionToken();
  if (!token) return { error: "Seu acesso expirou. Informe o CPF novamente." };
  if (!payload.date || !payload.meal_schedule_id || payload.items.length < 1) {
    return { error: "Escolha a data, o horário e ao menos um item." };
  }
  try {
    const order = await apiRequest<Order>("/api/v1/employee/orders", {
      method: "POST",
      token,
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    });
    revalidatePath("/empresa");
    revalidatePath("/cozinha");
    return { order };
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível criar o pedido.",
    };
  }
}

export async function logoutEmployee() {
  const token = await employeeSessionToken();
  if (token) {
    try {
      await apiRequest<void>("/api/v1/employee/logout", {
        method: "POST",
        token,
      });
    } catch {
      // The local cookie must still be removed if the API is unavailable.
    }
  }
  await clearEmployeeSessionToken();
  redirect("/funcionario");
}

export async function createEmployeePixCheckoutAction(
  orderId: string,
): Promise<EmployeePixActionResult> {
  const token = await employeeSessionToken();
  if (!token) return { error: "Seu acesso expirou. Informe o CPF novamente." };
  try {
    const checkout = await apiRequest<PixCheckout>(
      `/api/v1/employee/orders/${orderId}/payments/pix`,
      { method: "POST", token },
    );
    return { checkout };
  } catch (error) {
    return {
      error: error instanceof ApiError ? error.message : "Não foi possível iniciar o Pix.",
    };
  }
}

export async function switchEmployeePaymentToDeliveryAction(
  orderId: string,
): Promise<EmployeeActionResult> {
  const token = await employeeSessionToken();
  if (!token) return { error: "Seu acesso expirou. Informe o CPF novamente." };
  try {
    const result = await apiRequest<{ order: Order }>(
      `/api/v1/employee/orders/${orderId}/payment-method/delivery`,
      { method: "POST", token },
    );
    revalidatePath("/empresa");
    revalidatePath("/cozinha");
    return { order: result.order };
  } catch (error) {
    return {
      error:
        error instanceof ApiError
          ? error.message
          : "Não foi possível alterar a forma de pagamento.",
    };
  }
}
