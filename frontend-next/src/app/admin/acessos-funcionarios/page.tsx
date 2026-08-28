import { EmployeeAccessManagement } from "@/components/employee-access-management";
import { requireRole } from "@/lib/auth";

export default async function AdminEmployeeAccessPage() {
  await requireRole("admin");
  return <EmployeeAccessManagement mode="admin" />;
}
