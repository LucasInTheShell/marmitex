import { CompanyPanel } from "@/app/empresa/panel";
import { requireRole } from "@/lib/auth";
import { orderCutoffTime } from "@/lib/env";

export default async function CompanyPage() {
  const account = await requireRole("company");

  return (
    <CompanyPanel
      company={{ id: account.company_id!, name: account.name }}
      cutoffTime={orderCutoffTime()}
    />
  );
}
