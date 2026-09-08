"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { accessEmployee } from "@/app/funcionario/actions";

export function EmployeeEntry() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function enter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const cpf = String(formData.get("cpf") ?? "").trim();

    if (cpf.replaceAll(/\D/g, "").length !== 11) {
      setError("Informe um CPF com 11 dígitos.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const result = await accessEmployee(cpf);
    setSubmitting(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    router.push("/funcionario/pedido");
  }

  return (
    <form onSubmit={enter} className="mt-8 space-y-5" noValidate>
      <label className="block text-sm font-semibold text-stone-700">
        CPF do funcionário
        <input
          name="cpf"
          inputMode="numeric"
          autoComplete="username"
          placeholder="000.000.000-00"
          maxLength={14}
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
        disabled={submitting}
        className="min-h-14 w-full rounded-xl bg-[#216450] px-5 text-base font-semibold text-white shadow-sm hover:bg-[#173f34] focus:outline-none focus:ring-4 focus:ring-emerald-200"
      >
        {submitting ? "Validando…" : "Entrar para fazer pedido"}
      </button>
      <p className="text-center text-xs leading-5 text-stone-500">
        Use o CPF cadastrado pela sua empresa. Não é necessário criar uma conta ou senha.
      </p>
    </form>
  );
}
