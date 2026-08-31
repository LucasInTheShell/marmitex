"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useOptimistic, useState, useTransition } from "react";

import { updateOrderStatusAction } from "@/app/cozinha/actions";
import { ThermalPrintDocument } from "@/components/thermal-print-document";
import { formatOrderDate } from "@/lib/demo-orders";
import {
  KITCHEN_STATUSES,
  formatMealTime,
  nextKitchenStatus,
} from "@/lib/orders";
import type {
  DailyProductionSummary,
  KitchenOrder,
  KitchenProductionStatus,
} from "@/lib/types";

const COLUMN_STYLE: Record<KitchenProductionStatus, { dot: string; top: string; empty: string }> = {
  pending: { dot: "bg-amber-500", top: "border-t-amber-500", empty: "bg-amber-50/50" },
  printed: { dot: "bg-sky-500", top: "border-t-sky-500", empty: "bg-sky-50/50" },
  separated: { dot: "bg-violet-500", top: "border-t-violet-500", empty: "bg-violet-50/50" },
  delivered: { dot: "bg-emerald-500", top: "border-t-emerald-500", empty: "bg-emerald-50/50" },
};
const NEXT_ACTION: Record<KitchenProductionStatus, string | null> = {
  pending: "Imprimir comanda",
  printed: "Marcar separado",
  separated: "Marcar entregue",
  delivered: null,
};
type PrintJob =
  | { type: "order"; order: KitchenOrder }
  | { type: "day"; orders: KitchenOrder[]; date: string };

type KitchenPanelProps = {
  selectedDate: string;
  today: string;
  tomorrow: string;
  initialOrders: KitchenOrder[];
  summary: DailyProductionSummary;
};

export function KitchenPanel({
  selectedDate,
  today,
  tomorrow,
  initialOrders,
  summary,
}: KitchenPanelProps) {
  const router = useRouter();
  const [orders, updateOrder] = useOptimistic(
    initialOrders,
    (current, updated: KitchenOrder) =>
      current.map((item) => item.id === updated.id ? updated : item),
  );
  const [companyFilter, setCompanyFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [printJob, setPrintJob] = useState<PrintJob | null>(null);
  const [message, setMessage] = useState("");
  const [isUpdating, startUpdate] = useTransition();
  const [isNavigating, startNavigation] = useTransition();

  useEffect(() => {
    const interval = window.setInterval(() => router.refresh(), 20_000);
    return () => window.clearInterval(interval);
  }, [router]);

  const companies = useMemo(
    () => Array.from(new Set(orders.map((order) => order.company_name))).sort(),
    [orders],
  );
  const visibleOrders = orders.filter((order) => {
    const matchesCompany = companyFilter === "all" || order.company_name === companyFilter;
    const term = search.trim().toLocaleLowerCase("pt-BR");
    const searchable = `${order.order_number} ${order.employee_name} ${order.company_name} ${order.items.map((item) => item.item_name).join(" ")}`.toLocaleLowerCase("pt-BR");
    return matchesCompany && (!term || searchable.includes(term));
  });
  const deliveredCount = orders.filter((order) => order.production_status === "delivered").length;
  const activeCount = orders.length - deliveredCount;

  function navigateTo(date: string) {
    startNavigation(() => router.replace(`/cozinha?date=${encodeURIComponent(date)}`));
  }

  function updateStatus(order: KitchenOrder, status: KitchenProductionStatus) {
    setMessage("");
    startUpdate(async () => {
      const result = await updateOrderStatusAction(order.id, status);
      if (result.error || !result.order) {
        setMessage(result.error ?? "Não foi possível atualizar o pedido.");
        return;
      }
      updateOrder(result.order);
      setMessage(`Pedido #${order.order_number} atualizado para ${statusLabel(status)}.`);
      router.refresh();
    });
  }

  useEffect(() => {
    if (!printJob) return;
    const printedOrder = printJob.type === "order" ? printJob.order : null;
    function finishPrint() {
      if (printedOrder?.production_status === "pending") {
        startUpdate(async () => {
          const result = await updateOrderStatusAction(printedOrder.id, "printed");
          if (result.order) {
            updateOrder(result.order);
            setMessage(`Comanda do pedido #${printedOrder.order_number} impressa.`);
            router.refresh();
          } else {
            setMessage(result.error ?? "A comanda foi impressa, mas o status não foi atualizado.");
          }
        });
      } else {
        setMessage("Mapa do dia enviado para a janela de impressão.");
      }
      setPrintJob(null);
    }
    window.addEventListener("afterprint", finishPrint, { once: true });
    const timer = window.setTimeout(() => window.print(), 120);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("afterprint", finishPrint);
    };
  }, [printJob, router, updateOrder]);

  function advance(order: KitchenOrder) {
    if (order.production_status === "pending") {
      setMessage("");
      setPrintJob({ type: "order", order });
      return;
    }
    const next = nextKitchenStatus(order.production_status);
    if (next) updateStatus(order, next);
  }

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <div className="mb-1 flex items-center gap-2 text-sm font-medium text-[#34725f]"><span className="size-2 rounded-full bg-emerald-500" />API conectada · atualização a cada 20 s</div>
          <h1 className="text-2xl font-semibold text-stone-900 sm:text-3xl">Produção da cozinha</h1>
          <p className="mt-2 text-sm text-stone-600">Resumo por horário e empresa, seguido dos pedidos individuais.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DateButton label="Hoje" active={selectedDate === today} disabled={isNavigating} onClick={() => navigateTo(today)} />
          <DateButton label="Amanhã" active={selectedDate === tomorrow} disabled={isNavigating} onClick={() => navigateTo(tomorrow)} />
          <input type="date" aria-label="Data dos pedidos" value={selectedDate} disabled={isNavigating} onChange={(event) => navigateTo(event.target.value)} className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm" />
          <button type="button" onClick={() => setPrintJob({ type: "day", orders, date: selectedDate })} disabled={!orders.length} className="rounded-md bg-stone-800 px-3 py-2 text-sm font-medium text-white disabled:bg-stone-300">Imprimir mapa do dia</button>
        </div>
      </header>

      {message ? <p role="status" className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">{message}</p> : null}

      <section className="grid overflow-hidden rounded-md border border-stone-200 bg-white sm:grid-cols-5">
        <Metric label="Pedidos" value={summary.total_orders} />
        <Metric label="Marmitas" value={summary.total_meals} tone="text-[#216450]" />
        <Metric label="Em produção" value={activeCount} tone="text-amber-700" />
        <Metric label="Empresas" value={summary.companies.length} tone="text-sky-700" />
        <Metric label="Entregues" value={deliveredCount} tone="text-emerald-700" last />
      </section>

      <section>
        <SectionHeading title="Resumo da produção por horário" description={`${formatOrderDate(selectedDate, true)} · quantidades consolidadas por prato e tamanho`} />
        <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          {summary.meal_times.length ? summary.meal_times.map((mealTime) => (
            <article key={mealTime.scheduled_for ?? "no-time"} className="rounded-md border border-stone-200 bg-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div><p className="text-xs font-semibold uppercase text-stone-500">Horário do almoço</p><h3 className="mt-1 text-2xl font-semibold text-stone-900">{formatMealTime(mealTime.meal_time)}</h3><p className="mt-1 text-xs text-stone-500">{mealTime.schedule_labels.join(" · ")}</p></div>
                <div className="text-right"><strong className="text-xl text-[#216450]">{mealTime.total_meals}</strong><p className="text-xs text-stone-500">marmitas · {mealTime.total_orders} pedidos</p></div>
              </div>
              <SummaryItems items={mealTime.items} />
            </article>
          )) : <EmptySummary text="Nenhuma produção programada para esta data." />}
        </div>
      </section>

      <section>
        <SectionHeading title="Resumo por empresa" description="Separação de volumes, horários e pratos de cada cliente" />
        <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          {summary.companies.length ? summary.companies.map((company) => (
            <article key={company.company_id} className="rounded-md border border-stone-200 bg-white p-5">
              <div className="flex items-start justify-between gap-4"><div><h3 className="font-semibold text-stone-900">{company.company_name}</h3><p className="mt-1 text-xs text-stone-500">{company.meal_times.map((time) => `${formatMealTime(time.meal_time)} · ${time.total_meals}`).join(" | ")}</p></div><div className="text-right"><strong className="text-xl text-[#216450]">{company.total_meals}</strong><p className="text-xs text-stone-500">marmitas</p></div></div>
              <SummaryItems items={company.items} />
            </article>
          )) : <EmptySummary text="Nenhuma empresa com pedidos nesta data." />}
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <SectionHeading title="Pedidos individuais" description="A etapa só pode avançar na sequência recebido → impresso → separado → entregue" compact />
          <div className="flex flex-col gap-2 sm:flex-row">
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar pedido, pessoa, empresa ou prato" className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm sm:w-80" />
            <select value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)} className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm sm:w-56"><option value="all">Todas as empresas</option>{companies.map((company) => <option key={company} value={company}>{company}</option>)}</select>
          </div>
        </div>
        <div className="overflow-x-auto pb-3">
          <div className="grid min-w-[1160px] grid-cols-4 gap-4">
            {KITCHEN_STATUSES.map((status) => {
              const columnOrders = visibleOrders.filter((order) => order.production_status === status.value);
              return (
                <section key={status.value} className={`min-h-[380px] overflow-hidden rounded-md border border-t-4 border-stone-200 bg-stone-50 ${COLUMN_STYLE[status.value].top}`}>
                  <header className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3"><div className="flex items-center gap-2"><span className={`size-2.5 rounded-full ${COLUMN_STYLE[status.value].dot}`} /><h3 className="text-sm font-semibold">{status.shortLabel}</h3></div><span className="grid size-7 place-items-center rounded-full bg-stone-100 text-xs font-semibold">{columnOrders.length}</span></header>
                  <div className="space-y-3 p-3">
                    {columnOrders.length ? columnOrders.map((order) => (
                      <article key={order.id} className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
                        <div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-bold uppercase text-stone-400">Pedido #{order.order_number} · {formatMealTime(order.scheduled_for)}</p><p className="mt-1 truncate text-sm font-semibold">{order.employee_name}</p><p className="truncate text-xs font-medium text-[#34725f]">{order.company_name} · {order.employee_department}</p></div></div>
                        <ul className="my-3 divide-y divide-stone-100 border-y border-stone-100">
                          {order.items.map((item) => <li key={item.id} className="py-2 text-sm"><strong>{item.quantity}× {item.item_name}</strong> · {item.size}{item.notes ? <p className="mt-1 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">Obs.: {item.notes}</p> : null}</li>)}
                        </ul>
                        {NEXT_ACTION[status.value] ? <button type="button" disabled={isUpdating} onClick={() => advance(order)} className="w-full rounded-md bg-stone-800 px-3 py-2 text-xs font-semibold text-white disabled:bg-stone-400">{NEXT_ACTION[status.value]}</button> : <p className="text-center text-xs font-medium text-emerald-700">Fluxo concluído</p>}
                      </article>
                    )) : <div className={`rounded-md border border-dashed border-stone-200 px-4 py-10 text-center text-xs text-stone-500 ${COLUMN_STYLE[status.value].empty}`}>Nenhum pedido nesta etapa</div>}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </section>

      {printJob ? <ThermalPrintDocument {...printJob} /> : null}
    </div>
  );
}

function statusLabel(status: KitchenProductionStatus) {
  return KITCHEN_STATUSES.find((item) => item.value === status)?.shortLabel.toLocaleLowerCase("pt-BR") ?? status;
}

function SummaryItems({ items }: { items: DailyProductionSummary["meal_times"][number]["items"] }) {
  return <ul className="mt-4 divide-y divide-stone-100 border-t border-stone-100">{items.map((item) => <li key={item.menu_item_id} className="flex items-start justify-between gap-4 py-2 text-sm"><span className="text-stone-700">{item.item_name}<small className="ml-2 text-stone-400">{item.sizes.map((size) => `${size.size}: ${size.quantity}`).join(" · ")}</small></span><strong className="tabular-nums">{item.total_quantity}</strong></li>)}</ul>;
}

function SectionHeading({ title, description, compact = false }: { title: string; description: string; compact?: boolean }) {
  return <div className={compact ? "" : "mb-4"}><h2 className="text-lg font-semibold text-stone-900">{title}</h2><p className="mt-1 text-sm text-stone-500">{description}</p></div>;
}

function EmptySummary({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-stone-300 bg-white px-5 py-10 text-center text-sm text-stone-500">{text}</p>;
}

function DateButton({ label, active, disabled, onClick }: { label: string; active: boolean; disabled: boolean; onClick: () => void }) {
  return <button type="button" disabled={disabled} onClick={onClick} className={`rounded-md px-3 py-2 text-sm font-medium ${active ? "bg-[#216450] text-white" : "border border-stone-300 bg-white text-stone-700"}`}>{label}</button>;
}

function Metric({ label, value, tone = "text-stone-900", last = false }: { label: string; value: number; tone?: string; last?: boolean }) {
  return <div className={`border-b border-stone-200 px-5 py-4 sm:border-b-0 ${last ? "" : "sm:border-r"}`}><p className="text-xs font-medium uppercase text-stone-500">{label}</p><p className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>{value}</p></div>;
}
