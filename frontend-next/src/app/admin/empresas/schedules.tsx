"use client";

import { useActionState } from "react";

import type { MealSchedule } from "@/lib/types";

import {
  addMealSchedule,
  type MealScheduleFormState,
  updateMealSchedule,
} from "./actions";

const initialState: MealScheduleFormState = {};
const WEEKDAYS = [
  { value: 1, label: "Seg" },
  { value: 2, label: "Ter" },
  { value: 3, label: "Qua" },
  { value: 4, label: "Qui" },
  { value: 5, label: "Sex" },
  { value: 6, label: "Sáb" },
  { value: 7, label: "Dom" },
];

export function CompanySchedules({
  companyId,
  schedules,
}: {
  companyId: string;
  schedules: MealSchedule[];
}) {
  return (
    <div className="mt-4 space-y-3 border-t border-stone-100 pt-4">
      {schedules.map((schedule) => (
        <ScheduleEditor
          key={schedule.id}
          companyId={companyId}
          schedule={schedule}
        />
      ))}
      <AddScheduleForm companyId={companyId} />
    </div>
  );
}

function ScheduleEditor({
  companyId,
  schedule,
}: {
  companyId: string;
  schedule: MealSchedule;
}) {
  const action = updateMealSchedule.bind(null, companyId, schedule.id);
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <form
      action={formAction}
      className="rounded-md border border-stone-200 bg-stone-50 p-3"
    >
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_130px_auto_auto] sm:items-end">
        <label className="text-xs text-stone-600">
          Nome
          <input
            name="label"
            required
            maxLength={80}
            defaultValue={schedule.label}
            className="mt-1 w-full rounded-md border border-stone-300 bg-white px-2.5 py-2 text-sm text-stone-800"
          />
        </label>
        <label className="text-xs text-stone-600">
          Hora
          <input
            name="meal_time"
            type="time"
            required
            defaultValue={schedule.meal_time.slice(0, 5)}
            className="mt-1 w-full rounded-md border border-stone-300 bg-white px-2.5 py-2 text-sm text-stone-800"
          />
        </label>
        <label className="flex min-h-10 items-center gap-2 text-xs text-stone-600">
          <input name="active" type="checkbox" defaultChecked={schedule.active} />
          Ativo
        </label>
        <button
          type="submit"
          disabled={pending}
          className="rounded-md border border-stone-300 bg-white px-3 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-100 disabled:opacity-50"
        >
          {pending ? "Salvando…" : "Salvar"}
        </button>
      </div>
      <WeekdayFields selected={schedule.weekdays} />
      <FormMessage state={state} />
    </form>
  );
}

function AddScheduleForm({ companyId }: { companyId: string }) {
  const action = addMealSchedule.bind(null, companyId);
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <form
      action={formAction}
      className="rounded-md border border-dashed border-stone-300 p-3"
    >
      <p className="mb-2 text-xs font-semibold uppercase text-stone-500">
        Adicionar horário
      </p>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_130px_auto] sm:items-end">
        <label className="text-xs text-stone-600">
          Nome
          <input
            name="label"
            required
            maxLength={80}
            placeholder="Ex.: Segundo turno"
            className="mt-1 w-full rounded-md border border-stone-300 px-2.5 py-2 text-sm text-stone-800"
          />
        </label>
        <label className="text-xs text-stone-600">
          Hora
          <input
            name="meal_time"
            type="time"
            required
            defaultValue="12:00"
            className="mt-1 w-full rounded-md border border-stone-300 px-2.5 py-2 text-sm text-stone-800"
          />
        </label>
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-stone-700 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-600 disabled:opacity-50"
        >
          {pending ? "Adicionando…" : "Adicionar"}
        </button>
      </div>
      <WeekdayFields selected={[1, 2, 3, 4, 5]} />
      <FormMessage state={state} />
    </form>
  );
}

function WeekdayFields({ selected }: { selected: number[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-3">
      {WEEKDAYS.map((day) => (
        <label
          key={day.value}
          className="flex items-center gap-1.5 text-xs text-stone-600"
        >
          <input
            type="checkbox"
            name="weekdays"
            value={day.value}
            defaultChecked={selected.includes(day.value)}
          />
          {day.label}
        </label>
      ))}
    </div>
  );
}

function FormMessage({ state }: { state: MealScheduleFormState }) {
  if (state.error) {
    return (
      <p role="alert" className="mt-2 text-xs text-red-600">
        {state.error}
      </p>
    );
  }
  if (state.success) {
    return (
      <p role="status" className="mt-2 text-xs text-green-700">
        {state.success}
      </p>
    );
  }
  return null;
}
