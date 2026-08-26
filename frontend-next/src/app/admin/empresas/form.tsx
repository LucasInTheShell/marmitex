"use client";

import { useActionState, useEffect, useRef } from "react";

import { createCompany, type CompanyFormState } from "./actions";

const initialState: CompanyFormState = {};

export function NewCompanyForm() {
  const [state, formAction, pending] = useActionState(
    createCompany,
    initialState,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.success) formRef.current?.reset();
  }, [state.success]);

  return (
    <form
      ref={formRef}
      action={formAction}
      className="rounded-xl border border-stone-200 bg-white p-5"
    >
      <h2 className="mb-4 font-medium text-stone-800">Nova empresa</h2>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="text-sm text-stone-700">
          Nome da empresa
          <input
            name="name"
            required
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          E-mail de acesso
          <input
            name="email"
            type="email"
            required
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          Senha de acesso
          <input
            name="password"
            type="password"
            minLength={8}
            required
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>
      </div>

      <p className="mt-3 text-xs text-stone-500">
        Esse acesso é compartilhado pelos colaboradores da empresa. Eles se
        identificam no momento do pedido.
      </p>

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
        disabled={pending}
        className="mt-4 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-60"
      >
        {pending ? "Cadastrando…" : "Cadastrar empresa"}
      </button>
    </form>
  );
}
