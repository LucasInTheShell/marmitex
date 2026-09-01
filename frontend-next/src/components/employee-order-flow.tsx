"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";

import { createEmployeeOrderAction } from "@/app/funcionario/actions";
import type { AvailableMenu, Employee, MenuItem, Order, SizeOption } from "@/lib/types";

type Step = "menu" | "details" | "review" | "success";
type CartItem = { menuItem: MenuItem; size: SizeOption; quantity: number; notes: string };

const STEP_LABELS = ["Identificação", "Cardápio", "Detalhes", "Revisão"];

export function EmployeeOrderFlow({ employee, availableMenus }: { employee: Employee; availableMenus: AvailableMenu[] }) {
  const [step, setStep] = useState<Step>("menu");
  const [selectedDate, setSelectedDate] = useState(availableMenus[0]?.date ?? "");
  const selectedMenu = availableMenus.find((menu) => menu.date === selectedDate);
  const [scheduleId, setScheduleId] = useState(availableMenus[0]?.available_schedules[0]?.id ?? "");
  const [selectedDish, setSelectedDish] = useState<MenuItem | null>(null);
  const [size, setSize] = useState<SizeOption>("M");
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const total = useMemo(() => cart.reduce((sum, item) => sum + Number(item.menuItem.price ?? 0) * item.quantity, 0), [cart]);
  const currentStep = { menu: 1, details: 2, review: 3, success: 4 }[step];

  function chooseDate(date: string) {
    const menu = availableMenus.find((candidate) => candidate.date === date);
    setSelectedDate(date);
    setScheduleId(menu?.available_schedules[0]?.id ?? "");
    setCart([]);
    setError(null);
  }

  function selectDish(dish: MenuItem) {
    setSelectedDish(dish);
    setSize(dish.size_options.includes("M") ? "M" : dish.size_options[0]);
    setQuantity(1);
    setNotes("");
    setStep("details");
    setError(null);
  }

  function addItem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDish) return;
    const sameItem = cart.findIndex((item) => item.menuItem.id === selectedDish.id && item.size === size);
    if (sameItem >= 0) {
      setCart((current) => current.map((item, index) => index === sameItem ? { ...item, quantity: Math.min(10, item.quantity + quantity), notes: notes || item.notes } : item));
    } else {
      setCart((current) => [...current, { menuItem: selectedDish, size, quantity, notes: notes.trim() }]);
    }
    setStep("menu");
  }

  function goToReview() {
    if (!selectedDate || !scheduleId || cart.length === 0) {
      setError("Escolha a data, o horário e ao menos uma marmita.");
      return;
    }
    setError(null);
    setStep("review");
  }

  async function confirm() {
    setSubmitting(true);
    setError(null);
    const result = await createEmployeeOrderAction(
      { date: selectedDate, meal_schedule_id: scheduleId, items: cart.map((item) => ({ menu_item_id: item.menuItem.id, size: item.size, quantity: item.quantity, notes: item.notes || null })) },
      crypto.randomUUID(),
    );
    setSubmitting(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    setOrder(result.order ?? null);
    setStep("success");
  }

  if (availableMenus.length === 0) {
    return <main className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6"><StepCard eyebrow={`Olá, ${employee.name}`} title="Nenhum cardápio disponível" description="Não há cardápios publicados com horários ainda abertos para sua empresa. Tente novamente mais tarde."><p className="mt-6 rounded-xl bg-stone-50 p-4 text-sm text-stone-600">Empresa: <strong>{employee.company_name}</strong> · Setor: {employee.department}</p></StepCard></main>;
  }

  const selectedSchedule = selectedMenu?.available_schedules.find((schedule) => schedule.id === scheduleId);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
      {step !== "success" ? <ol className="mb-6 grid grid-cols-4 gap-1 sm:mb-8 sm:gap-3" aria-label="Etapas do pedido">{STEP_LABELS.map((label, index) => <li key={label} className="min-w-0"><div className={`h-1.5 rounded-full ${index <= currentStep ? "bg-[#216450]" : "bg-stone-200"}`} /><span className={`mt-2 block truncate text-[11px] font-medium sm:text-sm ${index === currentStep ? "text-[#216450]" : "text-stone-500"}`}>{index + 1}. {label}</span></li>)}</ol> : null}

      {step === "menu" ? <section>
        <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-[#34725f]">Olá, {employee.name}</p><h1 className="mt-1 text-2xl font-semibold text-stone-900 sm:text-3xl">Escolha sua marmita</h1><p className="mt-2 text-sm text-stone-600">{employee.company_name} · {employee.department}</p></div><Link href="/funcionario" className="text-sm font-semibold text-[#216450] hover:underline">Alterar CPF</Link></div>
        <div className="mb-6 grid gap-4 rounded-2xl border border-stone-200 bg-white p-5 sm:grid-cols-2">
          <label className="text-sm font-semibold text-stone-700">Dia do almoço<select value={selectedDate} onChange={(event) => chooseDate(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border border-stone-300 bg-white px-3 font-normal">{availableMenus.map((menu) => <option key={menu.date} value={menu.date}>{dateLabel(menu.date)}</option>)}</select></label>
          <label className="text-sm font-semibold text-stone-700">Horário disponível<select value={scheduleId} onChange={(event) => setScheduleId(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border border-stone-300 bg-white px-3 font-normal">{selectedMenu?.available_schedules.map((schedule) => <option key={schedule.id} value={schedule.id}>{schedule.label} · {schedule.meal_time.slice(0, 5)}</option>)}</select></label>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{selectedMenu?.items.map((dish) => <button key={dish.id} type="button" onClick={() => selectDish(dish)} className="group overflow-hidden rounded-2xl border border-stone-200 bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:border-[#79a995] hover:shadow-md focus:outline-none focus:ring-4 focus:ring-emerald-100"><div className="relative h-40 bg-[#dcebe5]">{dish.image_url ? <Image src={dish.image_url} alt={dish.name} fill sizes="(max-width: 640px) 100vw, 33vw" className="object-cover" /> : <span className="grid h-full place-items-center text-sm font-semibold text-[#34725f]">Sem foto</span>}</div><div className="p-5"><div className="flex items-start justify-between gap-4"><h2 className="text-lg font-semibold text-stone-900">{dish.name}</h2><span className="shrink-0 font-semibold text-[#216450]">{money(dish.price)}</span></div><p className="mt-2 min-h-12 text-sm leading-6 text-stone-600">{dish.description || "Sem descrição."}</p><span className="mt-5 block min-h-12 rounded-xl bg-[#eef7f3] px-4 py-3 text-center text-sm font-semibold text-[#216450] group-hover:bg-[#216450] group-hover:text-white">Ver detalhes</span></div></button>)}</div>
        <div className="mt-6 rounded-2xl border border-stone-200 bg-white p-5"><div className="flex items-center justify-between gap-4"><div><h2 className="font-semibold text-stone-900">Seu pedido</h2><p className="text-sm text-stone-500">{cart.length} tipo(s) de marmita</p></div><strong className="text-[#216450]">{money(total)}</strong></div>{cart.length ? <ul className="mt-4 divide-y divide-stone-200">{cart.map((item, index) => <li key={`${item.menuItem.id}-${item.size}`} className="flex items-center justify-between gap-3 py-3 text-sm"><span>{item.quantity}× {item.menuItem.name} · {item.size}</span><button type="button" onClick={() => setCart((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="font-semibold text-red-600">Remover</button></li>)}</ul> : <p className="mt-4 text-sm text-stone-500">Escolha um prato acima para começar.</p>}{error ? <p role="alert" className="mt-4 text-sm font-medium text-red-600">{error}</p> : null}<button type="button" onClick={goToReview} disabled={!cart.length} className="mt-5 min-h-14 w-full rounded-xl bg-[#216450] px-5 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">Revisar pedido</button></div>
      </section> : null}

      {step === "details" && selectedDish ? <StepCard eyebrow="Passo 3 de 4" title={selectedDish.name} description={selectedDish.description || "Configure sua marmita."} back={() => setStep("menu")}><form onSubmit={addItem} className="mt-7 grid gap-7 lg:grid-cols-[1fr_320px]"><div className="space-y-7"><DishImageCarousel dish={selectedDish} /><fieldset><legend className="text-sm font-semibold text-stone-800">Escolha o tamanho</legend><div className="mt-3 grid grid-cols-3 gap-3">{selectedDish.size_options.map((option) => <button key={option} type="button" aria-pressed={size === option} onClick={() => setSize(option)} className={`min-h-14 rounded-xl border text-base font-bold ${size === option ? "border-[#216450] bg-[#216450] text-white" : "border-stone-300 bg-white text-stone-700"}`}>{option}</button>)}</div></fieldset><div><p className="text-sm font-semibold text-stone-800">Quantidade</p><div className="mt-3 flex w-fit items-center overflow-hidden rounded-xl border border-stone-300 bg-white"><button type="button" aria-label="Diminuir quantidade" onClick={() => setQuantity((current) => Math.max(1, current - 1))} className="grid size-14 place-items-center text-2xl">−</button><output className="grid h-14 min-w-16 place-items-center border-x border-stone-300 text-lg font-bold">{quantity}</output><button type="button" aria-label="Aumentar quantidade" onClick={() => setQuantity((current) => Math.min(10, current + 1))} className="grid size-14 place-items-center text-2xl">+</button></div></div><label className="block text-sm font-semibold text-stone-800">Observações (opcional)<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} maxLength={300} placeholder="Ex.: sem cebola" className="mt-2 w-full rounded-xl border border-stone-300 px-4 py-3 font-normal outline-none" /></label></div><aside className="rounded-2xl bg-[#eef7f3] p-5"><p className="text-xs font-semibold uppercase tracking-wide text-[#34725f]">Sua escolha</p><p className="mt-3 text-xl font-semibold text-[#17372f]">{selectedDish.name}</p><p className="mt-2 text-sm text-[#34725f]">Tamanho {size} · {quantity} unidade(s)</p><div className="my-5 border-t border-[#cfe2da]" /><p className="text-2xl font-semibold text-[#17372f]">{money(Number(selectedDish.price ?? 0) * quantity)}</p><button type="submit" className="mt-6 min-h-14 w-full rounded-xl bg-[#216450] px-5 font-semibold text-white">Adicionar ao pedido</button></aside></form></StepCard> : null}

      {step === "review" ? <StepCard eyebrow="Passo 4 de 4" title="Revise antes de confirmar" description="Confira os dados abaixo. O pedido será enviado para a cozinha." back={() => setStep("menu")}><div className="mt-7 grid gap-5 lg:grid-cols-2"><ReviewSection title="Funcionário"><ReviewRow label="Nome" value={employee.name} /><ReviewRow label="Setor" value={employee.department} />{employee.internal_id ? <ReviewRow label="Matrícula" value={employee.internal_id} /> : null}<ReviewRow label="Empresa" value={employee.company_name} /></ReviewSection><ReviewSection title="Entrega"><ReviewRow label="Data" value={dateLabel(selectedDate)} /><ReviewRow label="Horário" value={selectedSchedule ? `${selectedSchedule.label} · ${selectedSchedule.meal_time.slice(0, 5)}` : "—"} /><ReviewRow label="Total" value={money(total)} /></ReviewSection></div><ReviewSection title="Itens"><div className="space-y-3">{cart.map((item) => <ReviewRow key={`${item.menuItem.id}-${item.size}`} label={`${item.quantity}× ${item.menuItem.name}`} value={`${item.size} · ${money(Number(item.menuItem.price ?? 0) * item.quantity)}`} />)}</div></ReviewSection>{error ? <p role="alert" className="mt-5 text-sm font-medium text-red-600">{error}</p> : null}<div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><button type="button" onClick={() => setStep("menu")} className="min-h-14 rounded-xl border border-stone-300 px-5 font-semibold">Editar pedido</button><button type="button" onClick={confirm} disabled={submitting} className="min-h-14 rounded-xl bg-[#216450] px-6 font-semibold text-white disabled:opacity-70">{submitting ? "Confirmando…" : "Confirmar pedido"}</button></div></StepCard> : null}

      {step === "success" && order ? <section className="mx-auto max-w-2xl rounded-3xl border border-emerald-200 bg-white px-6 py-12 text-center shadow-sm sm:px-10"><span className="mx-auto grid size-20 place-items-center rounded-full bg-emerald-100 text-4xl text-emerald-700">✓</span><p className="mt-6 text-sm font-semibold uppercase tracking-wide text-emerald-700">Pedido confirmado</p><h1 className="mt-2 text-3xl font-semibold text-stone-900">Pedido realizado!</h1><p className="mx-auto mt-3 max-w-md text-sm leading-6 text-stone-600">Obrigado, {employee.name}. Seu pedido foi salvo e já está disponível para a cozinha.</p><div className="mx-auto mt-7 max-w-sm rounded-xl bg-stone-50 px-5 py-4 text-left text-sm"><ReviewRow label="Pedido" value={`#${order.order_number}`} /><ReviewRow label="Status" value="Recebido" /><ReviewRow label="Total" value={money(order.total_price)} /></div><Link href="/funcionario" className="mt-8 inline-grid min-h-14 place-items-center rounded-xl border border-stone-300 px-6 font-semibold text-stone-700">Finalizar acesso</Link></section> : null}
    </main>
  );
}

function money(value: number | null): string {
  return value == null ? "Preço indisponível" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "full", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`));
}

function DishImageCarousel({ dish }: { dish: MenuItem }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const images = useMemo(() => {
    const ordered = [...dish.images].sort((left, right) => left.sort_order - right.sort_order);
    const primary = ordered.find((image) => image.is_primary);
    if (primary) return [primary, ...ordered.filter((image) => image.id !== primary.id)];
    if (ordered.length) return ordered;
    return dish.image_url
      ? [{ id: dish.image_url, url: dish.image_url, sort_order: 0, is_primary: true }]
      : [];
  }, [dish]);

  if (!images.length) {
    return (
      <div className="grid h-72 place-items-center rounded-2xl bg-[#dcebe5] text-sm font-semibold text-[#34725f]">
        Sem fotos cadastradas
      </div>
    );
  }

  const currentImage = images[currentIndex];
  const hasMultipleImages = images.length > 1;
  const previous = () => setCurrentIndex((current) => (current - 1 + images.length) % images.length);
  const next = () => setCurrentIndex((current) => (current + 1) % images.length);

  return (
    <section aria-label={`Fotos de ${dish.name}`}>
      <div className="relative h-72 overflow-hidden rounded-2xl bg-stone-100 sm:h-96">
        <Image
          key={currentImage.id}
          src={currentImage.url}
          alt={`${dish.name} — foto ${currentIndex + 1} de ${images.length}`}
          fill
          sizes="(max-width: 1024px) 100vw, 700px"
          className="object-cover"
        />
        {hasMultipleImages ? (
          <>
            <button
              type="button"
              onClick={previous}
              aria-label="Ver foto anterior"
              className="absolute left-3 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-2xl text-stone-800 shadow-md hover:bg-white focus:outline-none focus:ring-4 focus:ring-white/60"
            >
              ‹
            </button>
            <button
              type="button"
              onClick={next}
              aria-label="Ver próxima foto"
              className="absolute right-3 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-2xl text-stone-800 shadow-md hover:bg-white focus:outline-none focus:ring-4 focus:ring-white/60"
            >
              ›
            </button>
            <span className="absolute bottom-3 right-3 rounded-full bg-stone-950/70 px-3 py-1 text-xs font-semibold text-white">
              {currentIndex + 1} / {images.length}
            </span>
          </>
        ) : null}
      </div>

      {hasMultipleImages ? (
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1" aria-label="Selecionar foto">
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              onClick={() => setCurrentIndex(index)}
              aria-label={`Ver foto ${index + 1}`}
              aria-current={index === currentIndex ? "true" : undefined}
              className={`relative h-16 w-20 shrink-0 overflow-hidden rounded-lg border-2 ${index === currentIndex ? "border-[#216450]" : "border-transparent opacity-70 hover:opacity-100"}`}
            >
              <Image src={image.url} alt="" fill sizes="80px" className="object-cover" />
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function StepCard({ eyebrow, title, description, back, children }: { eyebrow: string; title: string; description: string; back?: () => void; children: React.ReactNode }) {
  return <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-8"><div className="flex items-start gap-4">{back ? <button type="button" onClick={back} aria-label="Voltar" className="grid size-11 shrink-0 place-items-center rounded-xl border border-stone-300 text-xl">←</button> : null}<div><p className="text-sm font-semibold text-[#34725f]">{eyebrow}</p><h1 className="mt-1 text-2xl font-semibold text-stone-900 sm:text-3xl">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">{description}</p></div></div>{children}</section>;
}

function ReviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mt-5 rounded-xl border border-stone-200 bg-stone-50 p-5"><h2 className="mb-4 font-semibold text-stone-900">{title}</h2><dl className="space-y-3">{children}</dl></section>;
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between gap-4 border-b border-stone-200 pb-2 last:border-0 last:pb-0"><dt className="text-stone-500">{label}</dt><dd className="text-right font-semibold text-stone-800">{value}</dd></div>;
}
