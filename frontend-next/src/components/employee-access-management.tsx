"use client";

import Link from "next/link";
import { useState } from "react";

type EmployeeAccess = {
  id: string;
  company: string;
  username: string;
  status: "Ativo" | "Inativo" | "Pendente";
  lastAccess: string;
};

const INITIAL_ACCESSES: EmployeeAccess[] = [
  {
    id: "employee-acme",
    company: "Acme Ltda",
    username: "acme.funcionarios",
    status: "Ativo",
    lastAccess: "Hoje, 08:42",
  },
  {
    id: "employee-deltha",
    company: "Deltha Contabilidade",
    username: "deltha.funcionarios",
    status: "Pendente",
    lastAccess: "—",
  },
  {
    id: "employee-orbita",
    company: "Órbita Engenharia",
    username: "orbita.funcionarios",
    status: "Inativo",
    lastAccess: "22/08/2026, 09:14",
  },
];

export function EmployeeAccessManagement({
  mode,
  companyName,
}: {
  mode: "admin" | "company";
  companyName?: string;
}) {
  const [accesses, setAccesses] = useState(INITIAL_ACCESSES);
  const [showForm, setShowForm] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [companyAccess, setCompanyAccess] = useState<EmployeeAccess | null>(null);

  function simulateAction(message: string) {
    setNotice(`${message} Esta ação é apenas uma demonstração do frontend.`);
  }

  function createAdminAccess(formData: FormData) {
    const company = String(formData.get("company") ?? "").trim();
    const username = String(formData.get("username") ?? "").trim();
    if (!company || !username) return;

    setAccesses((current) => [
      {
        id: `employee-${Date.now()}`,
        company,
        username,
        status: "Pendente",
        lastAccess: "—",
      },
      ...current,
    ]);
    setShowForm(false);
    setNotice("Acesso adicionado à demonstração. Nenhum dado foi persistido.");
  }

  function createCompanyAccess(formData: FormData) {
    const username = String(formData.get("username") ?? "").trim();
    if (!username) return;

    setCompanyAccess({
      id: "employee-current-company",
      company: companyName ?? "Empresa",
      username,
      status: "Ativo",
      lastAccess: "—",
    });
    setShowForm(false);
    setNotice("Acesso criado apenas nesta demonstração visual.");
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
            Protótipo frontend
          </span>
          <h1 className="mt-3 text-2xl font-semibold text-stone-900 sm:text-3xl">
            {mode === "admin" ? "Acessos Employee" : "Acesso dos funcionários"}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
            {mode === "admin"
              ? "Visualize como será o gerenciamento do acesso compartilhado de funcionários de cada empresa."
              : "Configure visualmente o acesso compartilhado que ficará disponível no tablet ou dispositivo da empresa."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowForm((current) => !current);
            setNotice(null);
          }}
          className="min-h-11 rounded-md bg-[#216450] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#173f34]"
        >
          {showForm ? "Cancelar" : "Criar acesso Employee"}
        </button>
      </header>

      {notice ? (
        <p
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          {notice}
        </p>
      ) : null}

      {showForm ? (
        <form
          action={mode === "admin" ? createAdminAccess : createCompanyAccess}
          className="rounded-md border border-stone-200 bg-white p-5 sm:p-6"
        >
          <h2 className="font-semibold text-stone-900">Novo acesso compartilhado</h2>
          <p className="mt-1 text-sm text-stone-500">
            Os campos validam a experiência, mas não enviam dados ao backend.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {mode === "admin" ? (
              <label className="text-sm font-medium text-stone-700">
                Empresa
                <input
                  name="company"
                  required
                  placeholder="Nome da empresa"
                  className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                />
              </label>
            ) : (
              <div className="rounded-md bg-stone-50 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
                  Empresa vinculada
                </p>
                <p className="mt-1 font-semibold text-stone-900">{companyName}</p>
              </div>
            )}
            <label className="text-sm font-medium text-stone-700">
              Usuário Employee
              <input
                name="username"
                required
                defaultValue={
                  mode === "company"
                    ? `${(companyName ?? "empresa").toLocaleLowerCase("pt-BR").replaceAll(" ", ".")}.funcionarios`
                    : ""
                }
                placeholder="empresa.funcionarios"
                className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
              />
            </label>
          </div>
          <label className="mt-4 block max-w-md text-sm font-medium text-stone-700">
            Senha inicial
            <input
              type="password"
              required
              minLength={8}
              placeholder="Mínimo de 8 caracteres"
              className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
            />
          </label>
          <button
            type="submit"
            className="mt-5 min-h-11 rounded-md bg-stone-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-stone-700"
          >
            Simular criação
          </button>
        </form>
      ) : null}

      {mode === "admin" ? (
        <AdminAccessTable accesses={accesses} onAction={simulateAction} />
      ) : (
        <CompanyAccessCard
          access={companyAccess}
          companyName={companyName ?? "Empresa"}
          onAction={simulateAction}
        />
      )}

      <div className="flex flex-col gap-3 rounded-md border border-[#cfe2da] bg-[#eef7f3] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-[#17372f]">Pré-visualizar ambiente Employee</p>
          <p className="mt-1 text-sm text-[#34725f]">
            Abra o fluxo responsivo que será usado pelos funcionários.
          </p>
        </div>
        <Link
          href="/funcionario"
          className="rounded-md border border-[#34725f] px-4 py-2.5 text-center text-sm font-semibold text-[#216450] hover:bg-white"
        >
          Abrir demonstração
        </Link>
      </div>
    </div>
  );
}

function AdminAccessTable({
  accesses,
  onAction,
}: {
  accesses: EmployeeAccess[];
  onAction: (message: string) => void;
}) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-stone-900">Empresas e acessos</h2>
        <span className="text-xs text-stone-500">{accesses.length} registros simulados</span>
      </div>
      <div className="overflow-x-auto rounded-md border border-stone-200 bg-white">
        <table className="min-w-[820px] w-full text-left text-sm">
          <thead className="border-b border-stone-200 bg-stone-50 text-stone-600">
            <tr>
              <th className="px-5 py-3 font-medium">Empresa</th>
              <th className="px-5 py-3 font-medium">Usuário Employee</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Último acesso</th>
              <th className="px-5 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-200">
            {accesses.map((access) => (
              <tr key={access.id}>
                <td className="px-5 py-4 font-medium text-stone-900">{access.company}</td>
                <td className="px-5 py-4 text-stone-600">{access.username}</td>
                <td className="px-5 py-4">
                  <StatusBadge status={access.status} />
                </td>
                <td className="px-5 py-4 text-stone-500">{access.lastAccess}</td>
                <td className="px-5 py-4">
                  <div className="flex gap-3">
                    <TextButton onClick={() => onAction(`Edição de ${access.username} selecionada.`)}>
                      Editar
                    </TextButton>
                    <TextButton onClick={() => onAction(`Alteração de status de ${access.username} selecionada.`)}>
                      {access.status === "Inativo" ? "Ativar" : "Desativar"}
                    </TextButton>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CompanyAccessCard({
  access,
  companyName,
  onAction,
}: {
  access: EmployeeAccess | null;
  companyName: string;
  onAction: (message: string) => void;
}) {
  return (
    <section className="rounded-md border border-stone-200 bg-white p-5 sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
            Acesso compartilhado
          </p>
          <h2 className="mt-2 text-xl font-semibold text-stone-900">
            {access?.username ?? "Nenhum acesso configurado"}
          </h2>
          <p className="mt-1 text-sm text-stone-500">Empresa: {companyName}</p>
        </div>
        <StatusBadge status={access?.status ?? "Pendente"} />
      </div>

      <dl className="mt-6 grid gap-4 border-y border-stone-200 py-5 sm:grid-cols-3">
        <Info label="Usuário Employee" value={access?.username ?? "Aguardando criação"} />
        <Info label="Último acesso" value={access?.lastAccess ?? "—"} />
        <Info label="Dispositivo principal" value="Tablet da empresa" />
      </dl>

      <div className="mt-5 flex flex-wrap gap-2">
        <ActionButton onClick={() => onAction("Edição do acesso selecionada.")}>Editar</ActionButton>
        <ActionButton onClick={() => onAction("Desativação do acesso selecionada.")}>Desativar</ActionButton>
        <ActionButton onClick={() => onAction("Redefinição de senha selecionada.")}>Redefinir senha</ActionButton>
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: EmployeeAccess["status"] }) {
  const style = {
    Ativo: "bg-emerald-100 text-emerald-800",
    Inativo: "bg-stone-200 text-stone-700",
    Pendente: "bg-amber-100 text-amber-800",
  }[status];
  return <span className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${style}`}>{status}</span>;
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-stone-800">{value}</dd>
    </div>
  );
}

function ActionButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-10 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50"
    >
      {children}
    </button>
  );
}

function TextButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="font-medium text-[#216450] hover:underline">
      {children}
    </button>
  );
}
