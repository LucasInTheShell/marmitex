import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { CompanyWithAccess } from "@/lib/types";

import { NewCompanyForm } from "./form";
import { CompanySchedules } from "./schedules";

export default async function CompaniesPage() {
  await requireRole("admin");

  const companies = await apiRequest<CompanyWithAccess[]>("/api/v1/companies", {
    token: await sessionToken(),
  });

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold text-stone-800">Empresas</h1>

      <NewCompanyForm />

      <section>
        <h2 className="mb-3 font-medium text-stone-800">
          Empresas cadastradas
        </h2>

        {companies.length > 0 ? (
          <ul className="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
            {companies.map((company) => (
              <li
                key={company.id}
                className="px-5 py-4"
              >
                <div className="flex items-center justify-between gap-4">
                  <span className="font-medium text-stone-800">
                    {company.name}
                  </span>
                  <span className="text-sm text-stone-500">
                    {company.access_email}
                  </span>
                </div>
                <CompanySchedules
                  companyId={company.id}
                  schedules={company.meal_schedules}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-stone-500">Nenhuma empresa cadastrada.</p>
        )}
      </section>
    </div>
  );
}
