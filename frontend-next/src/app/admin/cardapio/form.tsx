"use client";

import { useActionState } from "react";

import type { Menu, MenuItem } from "@/lib/types";
import { shortDateLabel, weekdayLabel } from "@/lib/week";

import {
  publishWeekMenu,
  saveWeekMenu,
  type MenuFormState,
} from "./actions";

const initialState: MenuFormState = {};

type Props = {
  weekStart: string;
  days: string[];
  menuItems: MenuItem[];
  menusByDate: Record<string, Menu | undefined>;
};

export function WeekMenuForm({
  weekStart,
  days,
  menuItems,
  menusByDate,
}: Props) {
  const [saveState, saveAction, saving] = useActionState(
    saveWeekMenu,
    initialState,
  );
  const [publishState, publishAction, publishing] = useActionState(
    publishWeekMenu,
    initialState,
  );

  if (menuItems.length === 0) {
    return (
      <p className="rounded-xl border border-stone-200 bg-white p-5 text-sm text-stone-500">
        Cadastre pratos antes de montar o cardápio.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <form action={saveAction} className="space-y-4">
        <input type="hidden" name="weekStart" value={weekStart} />

        <div className="grid gap-4 md:grid-cols-2">
          {days.map((date) => {
            const menu = menusByDate[date];
            const selected = new Set(menu?.menu_item_ids ?? []);

            return (
              <fieldset
                key={date}
                className="rounded-xl border border-stone-200 bg-white p-5"
              >
                <legend className="px-1 text-sm font-medium text-stone-800">
                  {weekdayLabel(date)} · {shortDateLabel(date)}
                </legend>

                <p className="mb-3 text-xs">
                  {menu?.published ? (
                    <span
                      className="text-green-700"
                      data-testid={`status-${date}`}
                    >
                      Publicado
                    </span>
                  ) : (
                    <span
                      className="text-stone-500"
                      data-testid={`status-${date}`}
                    >
                      Não publicado
                    </span>
                  )}
                </p>

                <div className="space-y-2">
                  {menuItems.map((item) => (
                    <label
                      key={item.id}
                      className="flex items-center gap-2 text-sm text-stone-700"
                    >
                      <input
                        type="checkbox"
                        name={`dia-${date}`}
                        value={item.id}
                        defaultChecked={selected.has(item.id)}
                        className="size-4"
                      />
                      {item.name}
                    </label>
                  ))}
                </div>
              </fieldset>
            );
          })}
        </div>

        {saveState.error ? (
          <p role="alert" className="text-sm text-red-600">
            {saveState.error}
          </p>
        ) : null}
        {saveState.success ? (
          <p role="status" className="text-sm text-green-700">
            {saveState.success}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-60"
        >
          {saving ? "Salvando…" : "Salvar cardápio"}
        </button>
      </form>

      <form action={publishAction}>
        <input type="hidden" name="weekStart" value={weekStart} />

        {publishState.error ? (
          <p role="alert" className="mb-2 text-sm text-red-600">
            {publishState.error}
          </p>
        ) : null}
        {publishState.success ? (
          <p role="status" className="mb-2 text-sm text-green-700">
            {publishState.success}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={publishing}
          className="rounded-lg border border-stone-800 px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-60"
        >
          {publishing ? "Publicando…" : "Publicar semana"}
        </button>
      </form>
    </div>
  );
}
