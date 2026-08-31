"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import { createCompany, type CompanyFormState } from "./actions";

const initialState: CompanyFormState = {};
const WEEKDAYS = [
  { value: 1, label: "Seg" },
  { value: 2, label: "Ter" },
  { value: 3, label: "Qua" },
  { value: 4, label: "Qui" },
  { value: 5, label: "Sex" },
  { value: 6, label: "Sáb" },
  { value: 7, label: "Dom" },
];

function initialSchedules() {
  return [{ key: crypto.randomUUID(), label: "Almoço", time: "12:00" }];
}

export function NewCompanyForm() {
  const [state, formAction, pending] = useActionState(
    createCompany,
    initialState,
  );
  const formRef = useRef<HTMLFormElement>(null);
  const [schedules, setSchedules] = useState(initialSchedules);

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

      <fieldset className="mt-5 border-t border-stone-200 pt-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <legend className="text-sm font-medium text-stone-800">
              Horários de refeição
            </legend>
            <p className="mt-1 text-xs text-stone-500">
              Cadastre um horário para cada turno atendido pela empresa.
            </p>
          </div>
          <button
            type="button"
            disabled={schedules.length >= 8}
            onClick={() =>
              setSchedules((current) => [
                ...current,
                {
                  key: crypto.randomUUID(),
                  label: `Turno ${current.length + 1}`,
                  time: "12:00",
                },
              ])
            }
            className="rounded-md border border-stone-300 px-3 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50 disabled:opacity-50"
          >
            Adicionar horário
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {schedules.map((schedule, index) => (
            <div
              key={schedule.key}
              className="rounded-md border border-stone-200 bg-stone-50 p-4"
            >
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_150px_auto] sm:items-end">
                <label className="text-sm text-stone-700">
                  Nome do horário
                  <input
                    name="schedule_label"
                    defaultValue={schedule.label}
                    required
                    maxLength={80}
                    className="mt-1 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
                  />
                </label>
                <label className="text-sm text-stone-700">
                  Hora da refeição
                  <input
                    name="schedule_time"
                    type="time"
                    defaultValue={schedule.time}
                    required
                    className="mt-1 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
                  />
                </label>
                <button
                  type="button"
                  disabled={schedules.length === 1}
                  onClick={() =>
                    setSchedules((current) =>
                      current.filter((item) => item.key !== schedule.key),
                    )
                  }
                  className="rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-40"
                >
                  Remover
                </button>
              </div>
              <div className="mt-3 flex flex-wrap gap-3">
                {WEEKDAYS.map((day) => (
                  <label
                    key={day.value}
                    className="flex items-center gap-1.5 text-xs text-stone-600"
                  >
                    <input
                      type="checkbox"
                      name={`schedule_weekdays_${index}`}
                      value={day.value}
                      defaultChecked={day.value <= 5}
                    />
                    {day.label}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </fieldset>

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
