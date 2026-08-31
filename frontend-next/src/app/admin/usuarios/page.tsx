import { NewAccountForm } from "@/app/admin/usuarios/form";
import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { Account, CompanyWithAccess } from "@/lib/types";

const ROLE_LABELS = {
  admin: "Administrador",
  kitchen: "Cozinha",
  company: "Empresa",
} as const;

export default async function AccountsPage() {
  await requireRole("admin");
  const token = await sessionToken();

  const [accounts, companies] = await Promise.all([
    apiRequest<Account[]>("/api/v1/accounts", { token }),
    apiRequest<CompanyWithAccess[]>("/api/v1/companies", { token }),
  ]);
  const companyNames = new Map(
    companies.map((company) => [company.id, company.name]),
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-stone-800">Usuários</h1>
        <p className="mt-1 text-sm text-stone-500">
          Cada perfil recebe acesso somente à sua área do sistema.
        </p>
      </div>

      <NewAccountForm companies={companies.filter((company) => company.active)} />

      <section>
        <h2 className="mb-3 font-medium text-stone-800">
          Usuários cadastrados
        </h2>

        {accounts.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-stone-200 bg-stone-50 text-stone-600">
                <tr>
                  <th className="px-5 py-3 font-medium">Nome</th>
                  <th className="px-5 py-3 font-medium">E-mail</th>
                  <th className="px-5 py-3 font-medium">Perfil</th>
                  <th className="px-5 py-3 font-medium">Empresa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td className="px-5 py-3 font-medium text-stone-800">
                      {account.name}
                    </td>
                    <td className="px-5 py-3 text-stone-600">
                      {account.email}
                    </td>
                    <td className="px-5 py-3 text-stone-600">
                      {ROLE_LABELS[account.role]}
                    </td>
                    <td className="px-5 py-3 text-stone-500">
                      {account.company_id
                        ? (companyNames.get(account.company_id) ??
                          "Empresa indisponível")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-stone-500">Nenhum usuário cadastrado.</p>
        )}
      </section>
    </div>
  );
}
