import { EmployeeOrderFlow } from "@/components/employee-order-flow";
import { ApiError, apiRequest } from "@/lib/api/client";
import { employeeSessionToken } from "@/lib/employee-session";
import { appTimeZone } from "@/lib/env";
import type { AvailableMenu, Employee, Order } from "@/lib/types";
import { addDays, todayInTimeZone } from "@/lib/week";
import { redirect } from "next/navigation";

export default async function EmployeeOrderPage() {
  const token = await employeeSessionToken();
  if (!token) redirect("/funcionario");
  const start = todayInTimeZone(appTimeZone());
  const end = addDays(start, 13);
  const orderStart = addDays(start, -14);
  let employee: Employee;
  let availableMenus: AvailableMenu[];
  let orders: Order[];
  try {
    [employee, availableMenus, orders] = await Promise.all([
      apiRequest<Employee>("/api/v1/employee/me", { token }),
      apiRequest<AvailableMenu[]>(
        `/api/v1/employee/menus/available?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
        { token },
      ),
      apiRequest<Order[]>(
        `/api/v1/employee/orders?start=${encodeURIComponent(orderStart)}&end=${encodeURIComponent(end)}`,
        { token },
      ),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/funcionario");
    throw error;
  }
  return <EmployeeOrderFlow employee={employee} availableMenus={availableMenus} initialOrders={orders} />;
}
