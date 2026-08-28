"use client";

import { useMemo, useState } from "react";

import {
  PRODUCTION_STATUS,
  addCalendarDays,
  formatOrderDate,
  localIsoDate,
  nextProductionStatus,
  type DemoOrder,
} from "@/lib/demo-orders";
import { useDemoOrders } from "@/lib/use-demo-orders";
import type { ProductionStatus } from "@/lib/types";

const COLUMN_STYLE: Record<ProductionStatus, { dot: string; top: string; empty: string }> = {
  pending: { dot: "bg-amber-500", top: "border-t-amber-500", empty: "bg-amber-50/50" },
  printed: { dot: "bg-sky-500", top: "border-t-sky-500", empty: "bg-sky-50/50" },
  separated: { dot: "bg-violet-500", top: "border-t-violet-500", empty: "bg-violet-50/50" },
  delivered: { dot: "bg-emerald-500", top: "border-t-emerald-500", empty: "bg-emerald-50/50" },
};

const NEXT_ACTION: Record<ProductionStatus, string | null> = {
  pending: "Imprimir etiqueta",
  printed: "Marcar separado",
  separated: "Marcar entregue",
  delivered: null,
};

export function KitchenPanel() {
  const { orders, setOrderStatus } = useDemoOrders();
  const [selectedDate, setSelectedDate] = useState(localIsoDate());
  const [companyFilter, setCompanyFilter] = useState("all");
  const [search, setSearch] = useState("");

  const dayOrders = useMemo(
    () => orders.filter((order) => order.date === selectedDate),
    [orders, selectedDate],
  );
  const companies = useMemo(
    () => Array.from(new Set(dayOrders.map((order) => order.companyName))).sort(),
    [dayOrders],
  );
  const visibleOrders = dayOrders.filter((order) => {
    const matchesCompany = companyFilter === "all" || order.companyName === companyFilter;
    const normalizedSearch = search.trim().toLocaleLowerCase("pt-BR");
    const matchesSearch =
      !normalizedSearch ||
      `${order.employeeName} ${order.companyName} ${order.menuItemName}`
        .toLocaleLowerCase("pt-BR")
        .includes(normalizedSearch);
    return matchesCompany && matchesSearch;
  });

  const dishSummary = useMemo(() => {
    const counts = new Map<string, number>();
    dayOrders.forEach((order) => {
      const key = `${order.menuItemName} · ${order.size}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [dayOrders]);

  const activeCount = dayOrders.filter((order) => order.productionStatus !== "delivered").length;
  const companyCount = new Set(dayOrders.map((order) => order.companyId)).size;
  const deliveredCount = dayOrders.filter((order) => order.productionStatus === "delivered").length;

  function advance(order: DemoOrder) {
    const next = nextProductionStatus(order.productionStatus);
    if (next) setOrderStatus(order.id, next);
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <div className="mb-1 flex items-center gap-2 text-sm font-medium text-[#34725f]">
            <span className="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
            Operação em andamento
          </div>
          <h1 className="text-2xl font-semibold text-stone-900 sm:text-3xl">Fila da cozinha</h1>
          <p className="mt-2 text-sm text-stone-600">Pedidos agrupados por etapa, prontos para a equipe produzir e separar.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setSelectedDate(localIsoDate())}
            className={`rounded-md px-3 py-2 text-sm font-medium ${selectedDate === localIsoDate() ? "bg-[#216450] text-white" : "border border-stone-300 bg-white text-stone-700 hover:bg-stone-50"}`}
          >
            Hoje
          </button>
          <button
            type="button"
            onClick={() => setSelectedDate(addCalendarDays(localIsoDate(), 1))}
            className={`rounded-md px-3 py-2 text-sm font-medium ${selectedDate === addCalendarDays(localIsoDate(), 1) ? "bg-[#216450] text-white" : "border border-stone-300 bg-white text-stone-700 hover:bg-stone-50"}`}
          >
            Amanhã
          </button>
          <input
            type="date"
            aria-label="Data dos pedidos"
            value={selectedDate}
            onChange={(event) => setSelectedDate(event.target.value)}
            className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700 outline-none focus:border-[#34725f]"
          />
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-md border border-stone-800 bg-stone-800 px-3 py-2 text-sm font-medium text-white hover:bg-stone-700"
          >
            Imprimir mapa do dia
          </button>
        </div>
      </header>

      <section className="grid overflow-hidden rounded-md border border-stone-200 bg-white sm:grid-cols-4">
        <Metric label="Total do dia" value={dayOrders.length} />
        <Metric label="Em produção" value={activeCount} tone="text-amber-700" />
        <Metric label="Empresas" value={companyCount} tone="text-sky-700" />
        <Metric label="Entregues" value={deliveredCount} tone="text-emerald-700" last />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-md border border-stone-200 bg-white p-4 sm:p-5">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-stone-900">Visão da produção</h2>
              <p className="mt-1 text-xs text-stone-500">{formatOrderDate(selectedDate, true)}</p>
            </div>
            <p className="mt-2 text-xs text-stone-500 sm:mt-0">{dayOrders.length} marmitas programadas</p>
          </div>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-stone-100" aria-label={`${deliveredCount} de ${dayOrders.length} pedidos entregues`}>
            {PRODUCTION_STATUS.map((status) => {
              const count = dayOrders.filter((order) => order.productionStatus === status.value).length;
              const colors: Record<ProductionStatus, string> = {
                pending: "bg-amber-400",
                printed: "bg-sky-400",
                separated: "bg-violet-400",
                delivered: "bg-emerald-500",
              };
              return count ? (
                <span
                  key={status.value}
                  className={`inline-block h-full ${colors[status.value]}`}
                  style={{ width: `${(count / dayOrders.length) * 100}%` }}
                />
              ) : null;
            })}
          </div>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-stone-600">
            {PRODUCTION_STATUS.map((status) => (
              <span key={status.value} className="flex items-center gap-1.5">
                <span className={`size-2 rounded-full ${COLUMN_STYLE[status.value].dot}`} aria-hidden="true" />
                {status.shortLabel}: {dayOrders.filter((order) => order.productionStatus === status.value).length}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-stone-200 bg-white p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-stone-900">Contagem por prato</h2>
            <span className="text-xs text-stone-500">Prato · tamanho</span>
          </div>
          <div className="mt-3 divide-y divide-stone-100">
            {dishSummary.length ? dishSummary.slice(0, 4).map(([dish, count]) => (
              <div key={dish} className="flex items-center justify-between gap-4 py-2 text-sm">
                <span className="truncate text-stone-600">{dish}</span>
                <strong className="tabular-nums text-stone-900">{count}</strong>
              </div>
            )) : (
              <p className="py-4 text-sm text-stone-500">Sem pedidos para esta data.</p>
            )}
          </div>
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Etapas dos pedidos</h2>
            <p className="mt-1 text-sm text-stone-500">Atualize cada pedido conforme ele avança na cozinha.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label>
              <span className="sr-only">Buscar pedido</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar pessoa, empresa ou prato"
                className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-stone-400 focus:border-[#34725f] sm:w-72"
              />
            </label>
            <label>
              <span className="sr-only">Filtrar empresa</span>
              <select
                value={companyFilter}
                onChange={(event) => setCompanyFilter(event.target.value)}
                className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700 outline-none focus:border-[#34725f] sm:w-56"
              >
                <option value="all">Todas as empresas</option>
                {companies.map((company) => <option key={company} value={company}>{company}</option>)}
              </select>
            </label>
          </div>
        </div>

        <div className="overflow-x-auto pb-3">
          <div className="grid min-w-[1120px] grid-cols-4 gap-4">
            {PRODUCTION_STATUS.map((status) => {
              const columnOrders = visibleOrders.filter((order) => order.productionStatus === status.value);
              return (
                <section key={status.value} className={`min-h-[380px] overflow-hidden rounded-md border border-t-4 border-stone-200 bg-stone-50 ${COLUMN_STYLE[status.value].top}`}>
                  <header className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`size-2.5 rounded-full ${COLUMN_STYLE[status.value].dot}`} aria-hidden="true" />
                      <h3 className="text-sm font-semibold text-stone-900">{status.shortLabel}</h3>
                    </div>
                    <span className="grid size-7 place-items-center rounded-full bg-stone-100 text-xs font-semibold tabular-nums text-stone-700">{columnOrders.length}</span>
                  </header>
                  <div className="space-y-3 p-3">
                    {columnOrders.length ? columnOrders.map((order) => (
                      <article key={order.id} className="rounded-md border border-stone-200 bg-white p-4 shadow-sm shadow-stone-200/40">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-stone-900">{order.employeeName}</p>
                            <p className="mt-0.5 truncate text-xs font-medium text-[#34725f]">{order.companyName}</p>
                          </div>
                          <span className="rounded bg-stone-100 px-2 py-1 text-xs font-bold text-stone-700">{order.size}</span>
                        </div>
                        <div className="my-3 border-y border-stone-100 py-3">
                          <p className="text-sm font-medium text-stone-800">{order.menuItemName}</p>
                          <p className="mt-1 text-xs text-stone-500">{order.employeeDepartment} · final {order.employeePhone.slice(-4)}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <select
                            aria-label={`Estado do pedido de ${order.employeeName}`}
                            value={order.productionStatus}
                            onChange={(event) => setOrderStatus(order.id, event.target.value as ProductionStatus)}
                            className="min-w-0 flex-1 rounded-md border border-stone-300 bg-white px-2 py-2 text-xs text-stone-700 outline-none focus:border-[#34725f]"
                          >
                            {PRODUCTION_STATUS.map((option) => (
                              <option key={option.value} value={option.value}>{option.shortLabel}</option>
                            ))}
                          </select>
                          {NEXT_ACTION[order.productionStatus] ? (
                            <button
                              type="button"
                              onClick={() => advance(order)}
                              className="shrink-0 rounded-md bg-stone-800 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                            >
                              {NEXT_ACTION[order.productionStatus]}
                            </button>
                          ) : null}
                        </div>
                      </article>
                    )) : (
                      <div className={`rounded-md border border-dashed border-stone-200 px-4 py-10 text-center text-xs text-stone-500 ${COLUMN_STYLE[status.value].empty}`}>
                        Nenhum pedido nesta etapa
                      </div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  tone = "text-stone-900",
  last = false,
}: {
  label: string;
  value: number;
  tone?: string;
  last?: boolean;
}) {
  return (
    <div className={`border-b border-stone-200 px-5 py-4 sm:border-b-0 ${last ? "" : "sm:border-r"}`}>
      <p className="text-xs font-medium uppercase text-stone-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}
