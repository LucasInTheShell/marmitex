import { EmployeeAccessManagement } from "@/components/employee-access-management";
import { requireRole } from "@/lib/auth";

export default async function CompanyEmployeeAccessPage() {
  const account = await requireRole("company");
  return <EmployeeAccessManagement mode="company" companyName={account.name} />;
}
