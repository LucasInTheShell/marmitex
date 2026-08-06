"use client";

import { useActionState, useEffect, useRef } from "react";

import { SIZE_OPTIONS } from "@/lib/types";

import { createMenuItem, type MenuItemFormState } from "./actions";

const initialState: MenuItemFormState = {};

export function NewMenuItemForm() {
  const [state, formAction, pending] = useActionState(
    createMenuItem,
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
      <h2 className="mb-4 font-medium text-stone-800">Novo prato</h2>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm text-stone-700">
          Nome do prato
          <input
            name="name"
            required
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>

        <label className="text-sm text-stone-700">
          Preço (opcional)
          <input
            name="price"
            inputMode="decimal"
            placeholder="0,00"
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
          />
        </label>
      </div>

      <label className="mt-4 block text-sm text-stone-700">
        Descrição (opcional)
        <input
          name="description"
          className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 outline-none focus:border-stone-500"
        />
      </label>

      <fieldset className="mt-4">
        <legend className="text-sm text-stone-700">Tamanhos disponíveis</legend>
        <div className="mt-2 flex gap-4">
          {SIZE_OPTIONS.map((size) => (
            <label key={size} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                name="sizes"
                value={size}
                defaultChecked
                className="size-4"
              />
              {size}
            </label>
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
        {pending ? "Cadastrando…" : "Cadastrar prato"}
      </button>
    </form>
  );
}
