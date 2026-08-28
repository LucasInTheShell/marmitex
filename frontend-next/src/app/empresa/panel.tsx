"use client";

import { useMemo, useState, type FormEvent } from "react";

import {
  DEMO_MENU_ITEMS,
  PRODUCTION_STATUS,
  formatOrderDate,
  orderableBusinessDays,
  type DemoOrder,
} from "@/lib/demo-orders";
import { useDemoOrders } from "@/lib/use-demo-orders";
import type { ProductionStatus } from "@/lib/types";

const CURRENCY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const STATUS_STYLES: Record<ProductionStatus, string> = {
  pending: "bg-amber-50 text-amber-800 ring-amber-200",
  printed: "bg-sky-50 text-sky-800 ring-sky-200",
  separated: "bg-violet-50 text-violet-800 ring-violet-200",
  delivered: "bg-emerald-50 text-emerald-800 ring-emerald-200",
};

type CompanyPanelProps = {
  company: { id: string; name: string };
  cutoffTime: string;
};

export function CompanyPanel({ company, cutoffTime }: CompanyPanelProps) {
  const availableDates = useMemo(() => orderableBusinessDays(), []);
  const { orders, addOrder } = useDemoOrders(company);
  const [selectedMenuItem, setSelectedMenuItem] = useState(DEMO_MENU_ITEMS[0].id);
  const [selectedSize, setSelectedSize] = useState<DemoOrder["size"]>("M");
  const [selectedDate, setSelectedDate] = useState(availableDates[0]);
  const [statusFilter, setStatusFilter] = useState<"all" | ProductionStatus>("all");
  const [message, setMessage] = useState("");

  const companyOrders = useMemo(
    () =>
      orders
        .filter((order) => order.companyId === company.id)
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    [company.id, orders],
  );
  const filteredOrders = companyOrders.filter(
    (order) => statusFilter === "all" || order.productionStatus === statusFilter,
  );
  const activeOrders = companyOrders.filter(
    (order) => order.productionStatus !== "delivered",
  ).length;
  const deliveredOrders = companyOrders.filter(
    (order) => order.productionStatus === "delivered",
  ).length;
  const selectedDish = DEMO_MENU_ITEMS.find(
    (item) => item.id === selectedMenuItem,
  )!;

  function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const cpf = String(form.get("cpf") ?? "").replace(/\D/g, "");
    const phone = String(form.get("phone") ?? "").replace(/\D/g, "");

    if (cpf.length !== 11 || phone.length < 10) {
      setMessage("Confira o CPF e o telefone antes de enviar o pedido.");
      return;
    }

    addOrder({
      id: crypto.randomUUID(),
      companyId: company.id,
      companyName: company.name,
      date: selectedDate,
      menuItemId: selectedDish.id,
      menuItemName: selectedDish.name,
      size: selectedSize,
      employeeName: String(form.get("employeeName") ?? "").trim(),
      employeePhone: phone,
      employeeDepartment: String(form.get("department") ?? "").trim(),
      employeeCpf: cpf,
      quantity: 1,
      notes: "",
      productionStatus: "pending",
      createdAt: new Date().toISOString(),
    });

    event.currentTarget.reset();
    setSelectedMenuItem(DEMO_MENU_ITEMS[0].id);
    setSelectedSize("M");
    setMessage(`Pedido de ${selectedDish.name} confirmado para ${formatOrderDate(selectedDate)}.`);
    window.setTimeout(() => document.querySelector("#pedidos")?.scrollIntoView(), 150);
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="mb-1 text-sm font-medium text-[#34725f]">{company.name}</p>
          <h1 className="text-2xl font-semibold text-stone-900 sm:text-3xl">
            Pedidos de refeições
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
            Organize as refeições da equipe e acompanhe cada pedido até a entrega.
          </p>
        </div>
        <div className="flex items-center gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <span className="size-2 rounded-full bg-amber-500" aria-hidden="true" />
          Pedidos do dia até <strong>{cutoffTime}</strong>
        </div>
      </header>

      <section className="grid overflow-hidden rounded-md border border-stone-200 bg-white sm:grid-cols-3">
        <div className="border-b border-stone-200 px-5 py-4 sm:border-r sm:border-b-0">
          <p className="text-xs font-medium uppercase text-stone-500">Pedidos registrados</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{companyOrders.length}</p>
        </div>
        <div className="border-b border-stone-200 px-5 py-4 sm:border-r sm:border-b-0">
          <p className="text-xs font-medium uppercase text-stone-500">Em andamento</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-700">{activeOrders}</p>
        </div>
        <div className="px-5 py-4">
          <p className="text-xs font-medium uppercase text-stone-500">Entregues</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-700">{deliveredOrders}</p>
        </div>
      </section>

      <section id="novo-pedido" className="scroll-mt-24">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-stone-900">Novo pedido</h2>
          <p className="mt-1 text-sm text-stone-500">Informe os dados do colaborador e escolha a refeição.</p>
        </div>

        <form onSubmit={submitOrder} className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="overflow-hidden rounded-md border border-stone-200 bg-white">
            <fieldset className="border-b border-stone-200 p-5 sm:p-6">
              <legend className="mb-4 block text-sm font-semibold text-stone-800">
                1. Escolha o prato
              </legend>
              <div className="divide-y divide-stone-100 rounded-md border border-stone-200">
                {DEMO_MENU_ITEMS.map((item) => {
                  const selected = selectedMenuItem === item.id;
                  return (
                    <label
                      key={item.id}
                      className={`flex cursor-pointer items-start gap-3 px-4 py-4 transition-colors ${selected ? "bg-emerald-50/70" : "hover:bg-stone-50"}`}
                    >
                      <input
                        type="radio"
                        name="menuItem"
                        value={item.id}
                        checked={selected}
                        onChange={() => setSelectedMenuItem(item.id)}
                        className="mt-1 accent-[#216450]"
                      />
                      <span className={`mt-1 size-2.5 shrink-0 rounded-full ${item.accent}`} aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold text-stone-900">{item.name}</span>
                        <span className="mt-1 block text-sm leading-5 text-stone-500">{item.description}</span>
                      </span>
                      <span className="text-sm font-semibold text-stone-800">{CURRENCY.format(item.price)}</span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <div className="grid gap-5 border-b border-stone-200 p-5 sm:grid-cols-2 sm:p-6">
              <label className="block text-sm font-medium text-stone-700">
                2. Data da refeição
                <select
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                  className="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2.5 text-stone-900 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                >
                  {availableDates.map((date) => (
                    <option key={date} value={date}>
                      {formatOrderDate(date, true)}
                    </option>
                  ))}
                </select>
              </label>

              <fieldset>
                <legend className="text-sm font-medium text-stone-700">3. Tamanho</legend>
                <div className="mt-2 grid grid-cols-3 overflow-hidden rounded-md border border-stone-300">
                  {(["P", "M", "G"] as const).map((size) => (
                    <button
                      key={size}
                      type="button"
                      aria-pressed={selectedSize === size}
                      onClick={() => setSelectedSize(size)}
                      className={`h-[42px] border-r border-stone-300 text-sm font-semibold last:border-r-0 ${selectedSize === size ? "bg-[#216450] text-white" : "bg-white text-stone-700 hover:bg-stone-50"}`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </fieldset>
            </div>

            <fieldset className="p-5 sm:p-6">
              <legend className="mb-4 block text-sm font-semibold text-stone-800">
                4. Dados do colaborador
              </legend>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-stone-700">
                  Nome completo
                  <input
                    name="employeeName"
                    required
                    autoComplete="name"
                    className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="text-sm font-medium text-stone-700">
                  Departamento
                  <input
                    name="department"
                    required
                    className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="text-sm font-medium text-stone-700">
                  Telefone
                  <input
                    name="phone"
                    required
                    inputMode="tel"
                    placeholder="(11) 99999-9999"
                    className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none placeholder:text-stone-400 focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="text-sm font-medium text-stone-700">
                  CPF
                  <input
                    name="cpf"
                    required
                    inputMode="numeric"
                    placeholder="Somente números"
                    className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none placeholder:text-stone-400 focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
              </div>
            </fieldset>
          </div>

          <aside className="rounded-md border border-stone-200 bg-white p-5 xl:sticky xl:top-8">
            <p className="text-xs font-semibold uppercase text-stone-500">Resumo do pedido</p>
            <div className="mt-5 border-b border-stone-200 pb-5">
              <p className="font-semibold text-stone-900">{selectedDish.name}</p>
              <p className="mt-1 text-sm leading-5 text-stone-500">{selectedDish.description}</p>
            </div>
            <dl className="space-y-3 border-b border-stone-200 py-5 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-stone-500">Data</dt>
                <dd className="text-right font-medium">{formatOrderDate(selectedDate)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-stone-500">Tamanho</dt>
                <dd className="font-medium">{selectedSize}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-stone-500">Total</dt>
                <dd className="text-base font-semibold">{CURRENCY.format(selectedDish.price)}</dd>
              </div>
            </dl>
            <p className="my-4 text-xs leading-5 text-stone-500">
              Ao confirmar, o pedido entra automaticamente na fila da cozinha.
            </p>
            {message ? (
              <p role="status" className={`mb-3 rounded-md px-3 py-2 text-sm ${message.startsWith("Pedido de") ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>
                {message}
              </p>
            ) : null}
            <button
              type="submit"
              className="w-full rounded-md bg-[#216450] px-4 py-3 text-sm font-semibold text-white hover:bg-[#173f34] focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2"
            >
              Confirmar pedido
            </button>
          </aside>
        </form>
      </section>

      <section id="pedidos" className="scroll-mt-24 pb-8">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Pedidos da empresa</h2>
            <p className="mt-1 text-sm text-stone-500">Acompanhe o andamento das refeições registradas.</p>
          </div>
          <label className="text-sm font-medium text-stone-600">
            Estado
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as "all" | ProductionStatus)}
              className="ml-2 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-[#34725f]"
            >
              <option value="all">Todos</option>
              {PRODUCTION_STATUS.map((status) => (
                <option key={status.value} value={status.value}>{status.shortLabel}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="overflow-hidden rounded-md border border-stone-200 bg-white">
          {filteredOrders.length ? (
            <div className="divide-y divide-stone-200">
              {filteredOrders.map((order) => {
                const status = PRODUCTION_STATUS.find((item) => item.value === order.productionStatus)!;
                return (
                  <article key={order.id} className="grid gap-3 px-4 py-4 sm:grid-cols-[120px_minmax(0,1fr)_160px_130px] sm:items-center sm:px-5">
                    <div>
                      <p className="text-sm font-semibold text-stone-900">{formatOrderDate(order.date)}</p>
                      <p className="mt-0.5 text-xs text-stone-500">#{order.id.slice(-6).toUpperCase()}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-stone-900">{order.employeeName}</p>
                      <p className="truncate text-sm text-stone-500">{order.menuItemName} · Tam. {order.size} · {order.employeeDepartment}</p>
                    </div>
                    <span className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_STYLES[order.productionStatus]}`}>
                      {status.label}
                    </span>
                    <p className="text-sm text-stone-500 sm:text-right">
                      {new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(order.createdAt))}
                    </p>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="px-5 py-10 text-center text-sm text-stone-500">Nenhum pedido encontrado neste estado.</p>
          )}
        </div>
      </section>
    </div>
  );
}
