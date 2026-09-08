"use client";

import Image from "next/image";
import { useActionState, useEffect, useMemo, useRef, useState } from "react";

import { SIZE_OPTIONS, type MenuItem, type SizeOption } from "@/lib/types";

import {
  createMenuItem,
  deleteMenuItem,
  type MenuItemFormState,
  updateMenuItem,
} from "./actions";

const initialState: MenuItemFormState = {};
const MAX_IMAGES = 6;

export function NewMenuItemForm() {
  const [state, formAction, pending] = useActionState(createMenuItem, initialState);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.success) formRef.current?.reset();
  }, [state.success]);

  return (
    <form ref={formRef} action={formAction} className="rounded-xl border border-stone-200 bg-white p-5">
      <h2 className="mb-4 font-medium text-stone-800">Novo prato</h2>
      <MenuItemFields key={state.success ?? "new"} resetToken={state.success} />
      <FormMessage state={state} />
      <SubmitButton pending={pending} idle="Cadastrar prato" busy="Cadastrando…" />
    </form>
  );
}

export function MenuItemEditor({ item }: { item: MenuItem }) {
  const [state, updateAction, updating] = useActionState(updateMenuItem.bind(null, item.id), initialState);
  const [deleteState, deleteAction, deleting] = useActionState(deleteMenuItem.bind(null, item.id), initialState);

  return (
    <article className="rounded-xl border border-stone-200 bg-white p-5">
      <form action={updateAction}>
        <div className="mb-4 flex items-start gap-4">
          {item.image_url ? (
            <Image src={item.image_url} alt={`Foto principal de ${item.name}`} width={112} height={84} className="h-[84px] w-28 rounded-lg object-cover" />
          ) : (
            <div className="flex h-[84px] w-28 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-xs text-stone-400">Sem foto</div>
          )}
          <div className="min-w-0 flex-1">
            <h3 className="font-medium text-stone-800">{item.name}</h3>
            <p className="text-sm text-stone-500">{item.images.length} de {MAX_IMAGES} imagens cadastradas.</p>
          </div>
        </div>
        <MenuItemFields key={`${state.success ?? ""}:${JSON.stringify(item)}`} item={item} resetToken={state.success} />
        <FormMessage state={state} />
        <SubmitButton pending={updating} disabled={deleting} idle="Salvar alterações" busy="Salvando…" />
      </form>

      <form action={deleteAction} onSubmit={(event) => { if (!window.confirm(`Excluir o prato ${item.name}?`)) event.preventDefault(); }} className="mt-4 border-t border-stone-100 pt-4">
        <button type="submit" disabled={updating || deleting} className="text-sm font-medium text-red-700 hover:text-red-800 disabled:opacity-60">
          {deleting ? "Excluindo…" : "Excluir prato"}
        </button>
        <FormMessage state={deleteState} />
      </form>
    </article>
  );
}

function MenuItemFields({ item, resetToken }: { item?: MenuItem; resetToken?: string }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm text-stone-700">Nome do prato<input name="name" required defaultValue={item?.name} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900" /></label>

      </div>
      <label className="mt-4 block text-sm text-stone-700">Descrição (opcional)<input name="description" defaultValue={item?.description ?? ""} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900" /></label>
      <ImageGalleryFields
        key={`${item?.id ?? "new"}:${resetToken ?? ""}:${item?.images.map((image) => image.id).join(",") ?? ""}`}
        item={item}
      />
      <PricingFields item={item} />
    </>
  );
}

function PricingFields({ item }: { item?: MenuItem }) {
  const [mode, setMode] = useState(item && Object.keys(item.size_prices ?? {}).length ? "sizes" : "single");
  const [sizes, setSizes] = useState<SizeOption[]>(item?.size_options ?? [...SIZE_OPTIONS]);
  return (
    <fieldset className="mt-4 rounded-lg border border-stone-200 p-4">
      <legend className="px-1 text-sm font-medium text-stone-700">Tamanhos e preços</legend>
      <label className="block text-sm text-stone-700">Como cobrar
        <select name="pricing_mode" value={mode} onChange={(event) => setMode(event.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2">
          <option value="single">Preço único para todos os tamanhos</option>
          <option value="sizes">Preço diferente por tamanho</option>
        </select>
      </label>
      <label className={mode === "single" ? "mt-3 block text-sm text-stone-700" : "hidden"}>Preço único (R$, opcional)
        <input name="price" disabled={mode !== "single"} inputMode="decimal" placeholder="0,00" defaultValue={item?.price?.toFixed(2).replace(".", ",") ?? ""} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2" />
      </label>
      <p className="mt-3 text-xs text-stone-500">{mode === "sizes" ? "Selecione os tamanhos disponíveis e informe o preço de cada um." : "Selecione os tamanhos disponíveis. O mesmo preço será aplicado a todos."}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {SIZE_OPTIONS.map((size) => (
          <div key={size} className="rounded-lg border border-stone-200 p-3">
            <label className="flex items-center gap-2 text-sm font-medium">
              <input type="checkbox" name="sizes" value={size} checked={sizes.includes(size)} onChange={(event) => setSizes((current) => event.target.checked ? [...current, size] : current.filter((value) => value !== size))} className="size-4" />
              Tamanho {size}
            </label>
            <label className={mode === "sizes" ? "mt-2 block text-xs text-stone-600" : "hidden"}>Preço {size} (R$)
              <input name={`price_${size}`} inputMode="decimal" required={mode === "sizes" && sizes.includes(size)} disabled={mode !== "sizes" || !sizes.includes(size)} defaultValue={(item?.size_prices?.[size] ?? item?.price)?.toFixed(2).replace(".", ",") ?? ""} placeholder="0,00" className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm disabled:bg-stone-100" />
            </label>
          </div>
        ))}
      </div>
    </fieldset>
  );
}

function ImageGalleryFields({ item }: { item?: MenuItem }) {
  const sortedExisting = useMemo(
    () => [...(item?.images ?? [])].sort((left, right) => left.sort_order - right.sort_order),
    [item?.images],
  );
  const initialPrimary = sortedExisting.find((image) => image.is_primary)?.id;
  const [previews, setPreviews] = useState<string[]>([]);
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [primary, setPrimary] = useState(initialPrimary ? `existing:${initialPrimary}` : "");

  useEffect(() => () => { for (const preview of previews) URL.revokeObjectURL(preview); }, [previews]);
  function selectFiles(files: FileList | null) {
    const selected = Array.from(files ?? []).slice(0, MAX_IMAGES);
    setPreviews(selected.map((file) => URL.createObjectURL(file)));
    if (!primary && selected.length) setPrimary("new:0");
    if (primary.startsWith("new:") && Number(primary.slice(4)) >= selected.length) {
      setPrimary(selected.length ? "new:0" : "");
    }
  }

  function toggleRemoval(imageId: string, checked: boolean) {
    const next = new Set(removed);
    if (checked) next.add(imageId); else next.delete(imageId);
    setRemoved(next);
    if (checked && primary === `existing:${imageId}`) {
      const replacement = sortedExisting.find((image) => image.id !== imageId && !next.has(image.id));
      setPrimary(replacement ? `existing:${replacement.id}` : previews.length ? "new:0" : "");
    }
  }

  const primaryExisting = primary.startsWith("existing:") ? primary.slice(9) : "";
  const primaryNewIndex = primary.startsWith("new:") ? primary.slice(4) : "";

  return (
    <fieldset className="mt-4 rounded-lg border border-stone-200 p-4">
      <legend className="px-1 text-sm font-medium text-stone-700">Galeria do prato</legend>
      <input type="hidden" name="existing_image_count" value={sortedExisting.length} />
      {primaryExisting ? <input type="hidden" name="primary_image_id" value={primaryExisting} /> : null}
      {primaryNewIndex ? <input type="hidden" name="primary_new_image_index" value={primaryNewIndex} /> : null}

      {sortedExisting.length ? (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {sortedExisting.map((image) => (
            <div key={image.id} className={`rounded-lg border p-2 ${removed.has(image.id) ? "opacity-45" : "border-stone-200"}`}>
              <Image src={image.url} alt="" width={160} height={110} className="h-24 w-full rounded-md object-cover" />
              <label className="mt-2 flex items-center gap-2 text-xs"><input type="radio" checked={primary === `existing:${image.id}`} disabled={removed.has(image.id)} onChange={() => setPrimary(`existing:${image.id}`)} />Principal</label>
              <label className="mt-1 flex items-center gap-2 text-xs text-red-700"><input type="checkbox" name="remove_image_ids" value={image.id} checked={removed.has(image.id)} onChange={(event) => toggleRemoval(image.id, event.target.checked)} />Remover</label>
            </div>
          ))}
        </div>
      ) : null}

      <label className="block text-sm text-stone-700">Adicionar imagens (JPEG, PNG ou WebP; até 5 MB cada)
        <input type="file" name="images" multiple accept="image/jpeg,image/png,image/webp" onChange={(event) => selectFiles(event.target.files)} className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-stone-100 file:px-3 file:py-2" />
      </label>
      <p className="mt-1 text-xs text-stone-500">Até {MAX_IMAGES} imagens no total. A principal aparece nos cards; as demais formam o carrossel.</p>

      {previews.length ? (
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {previews.map((preview, index) => (
            <label key={preview} className="rounded-lg border border-dashed border-stone-300 p-2 text-xs">
              <Image src={preview} alt="Prévia da nova imagem" width={160} height={110} unoptimized className="h-24 w-full rounded-md object-cover" />
              <span className="mt-2 flex items-center gap-2"><input type="radio" checked={primary === `new:${index}`} onChange={() => setPrimary(`new:${index}`)} />Usar como principal</span>
            </label>
          ))}
        </div>
      ) : null}
    </fieldset>
  );
}

function SubmitButton({ pending, disabled, idle, busy }: { pending: boolean; disabled?: boolean; idle: string; busy: string }) {
  return <button type="submit" disabled={pending || disabled} className="mt-4 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">{pending ? busy : idle}</button>;
}

function FormMessage({ state }: { state: MenuItemFormState }) {
  if (state.error) return <p role="alert" className="mt-3 text-sm text-red-600">{state.error}</p>;
  if (state.success) return <p role="status" className="mt-3 text-sm text-green-700">{state.success}</p>;
  return null;
}
