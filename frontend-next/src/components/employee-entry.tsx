"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function EmployeeEntry() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  function enter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const accessCode = String(formData.get("accessCode") ?? "").trim();

    if (accessCode.length < 4) {
      setError("Informe pelo menos 4 caracteres para simular o acesso.");
      return;
    }

    router.push("/funcionario/pedido");
  }

  return (
    <form onSubmit={enter} className="mt-8 space-y-5" noValidate>
      <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
          Empresa
        </p>
        <p className="mt-1 text-lg font-semibold text-stone-900">Acme Ltda</p>
        <p className="mt-1 text-sm text-stone-500">Tablet da recepção</p>
      </div>

      <label className="block text-sm font-semibold text-stone-700">
        Código de acesso do dispositivo
        <input
          name="accessCode"
          inputMode="numeric"
          autoComplete="off"
          placeholder="Digite o código de demonstração"
          aria-describedby={error ? "employee-entry-error" : undefined}
          className="mt-2 min-h-14 w-full rounded-xl border border-stone-300 bg-white px-4 text-lg outline-none placeholder:text-sm placeholder:text-stone-400 focus:border-[#34725f] focus:ring-4 focus:ring-emerald-100"
        />
      </label>

      {error ? (
        <p id="employee-entry-error" role="alert" className="text-sm font-medium text-red-600">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        className="min-h-14 w-full rounded-xl bg-[#216450] px-5 text-base font-semibold text-white shadow-sm hover:bg-[#173f34] focus:outline-none focus:ring-4 focus:ring-emerald-200"
      >
        Entrar para fazer pedido
      </button>
      <p className="text-center text-xs leading-5 text-stone-500">
        Use qualquer código com 4 ou mais caracteres. Nenhuma autenticação é realizada nesta demonstração.
      </p>
    </form>
  );
}
