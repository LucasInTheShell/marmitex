import { requireRole } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import type { Account, Company } from "@/lib/types";

import { NewCompanyForm } from "./form";

type CompanyWithAccounts = Company & { accounts: Pick<Account, "email">[] };

export default async function CompaniesPage() {
  await requireRole("admin");

  const supabase = await createClient();
  const { data: companies } = await supabase
    .from("companies")
    .select("id, name, active, created_at, accounts(email)")
    .order("name")
    .returns<CompanyWithAccounts[]>();

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold text-stone-800">Empresas</h1>

      <NewCompanyForm />

      <section>
        <h2 className="mb-3 font-medium text-stone-800">
          Empresas cadastradas
        </h2>

        {companies && companies.length > 0 ? (
          <ul className="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
            {companies.map((company) => (
              <li
                key={company.id}
                className="flex items-center justify-between px-5 py-3"
              >
                <span className="font-medium text-stone-800">
                  {company.name}
                </span>
                <span className="text-sm text-stone-500">
                  {company.accounts[0]?.email ?? "sem acesso"}
                </span>
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
