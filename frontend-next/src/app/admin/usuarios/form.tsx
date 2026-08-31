"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import type { AccountRole, Company } from "@/lib/types";

import { createAccount, type AccountFormState } from "./actions";

const initialState: AccountFormState = {};

const ROLE_HELP: Record<AccountRole, string> = {
  admin: "Acessa empresas, usuários, pratos e cardápios.",
  kitchen: "Acessa somente a fila de produção da cozinha.",
  company: "Acessa somente pedidos da empresa vinculada.",
};

export function NewAccountForm({ companies }: { companies: Company[] }) {
  const [state, formAction, pending] = useActionState(
    createAccount,
    initialState,
  );
  const [role, setRole] = useState<AccountRole>("kitchen");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.success) {
      formRef.current?.reset();
    }
  }, [state.success]);

  return (
    <form
      ref={formRef}
      action={formAction}
      className="rounded-xl border border-stone-200 bg-white p-5"
    >
      <h2 className="mb-4 font-medium text-stone-800">Novo usuário</h2>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm text-stone-700">
          Nome
          <input
            name="name"
            required
            maxLength={160}
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          E-mail
          <input
            name="email"
            type="email"
            required
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          Senha inicial
          <input
            name="password"
            type="password"
            minLength={8}
            required
            autoComplete="new-password"
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          Perfil de acesso
          <select
            name="role"
            value={role}
            onChange={(event) => setRole(event.target.value as AccountRole)}
            className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          >
            <option value="kitchen">Cozinha</option>
            <option value="company">Empresa</option>
            <option value="admin">Administrador</option>
          </select>
        </label>
      </div>

      {role === "company" ? (
        <label className="mt-4 block max-w-md text-sm text-stone-700">
          Empresa vinculada
          <select
            name="company_id"
            required
            defaultValue=""
            className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          >
            <option value="" disabled>
              Selecione uma empresa
            </option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <p className="mt-3 text-xs text-stone-500">{ROLE_HELP[role]}</p>

      {state.error ? (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {state.error}
        </p>
      ) : null}
      {state.success ? (
        <p role="status" className="mt-3 text-sm text-green-700">
          {state.success}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending || (role === "company" && companies.length === 0)}
        className="mt-4 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-60"
      >
        {pending ? "Criando…" : "Criar usuário"}
      </button>
    </form>
  );
}
