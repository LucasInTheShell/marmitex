"use client";

import { useActionState } from "react";

import {
  updateOperationalSettings,
  type OperationalSettingsFormState,
} from "./actions";

const initialState: OperationalSettingsFormState = {};

export function OperationalSettingsForm({ minutes }: { minutes: number }) {
  const [state, formAction, pending] = useActionState(
    updateOperationalSettings,
    initialState,
  );

  return (
    <form
      action={formAction}
      className="max-w-2xl rounded-xl border border-stone-200 bg-white p-5"
    >
      <h2 className="font-medium text-stone-800">Janela para novos pedidos</h2>
      <p className="mt-2 text-sm leading-6 text-stone-500">
        O sistema subtrai esta antecedência de cada horário de refeição da
        empresa. Por exemplo, 90 minutos antes de um almoço às 12:30 resulta em
        corte às 11:00.
      </p>

      <label className="mt-5 block max-w-xs text-sm font-medium text-stone-700">
        Antecedência global (minutos)
        <input
          name="order_cutoff_lead_minutes"
          type="number"
          min={0}
          max={1440}
          step={5}
          required
          defaultValue={minutes}
          className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 text-stone-900 outline-none focus:border-[#34725f]"
        />
      </label>

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
        className="mt-5 rounded-md bg-stone-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-stone-700 disabled:opacity-60"
      >
        {pending ? "Salvando…" : "Salvar configuração"}
      </button>
    </form>
  );
}
