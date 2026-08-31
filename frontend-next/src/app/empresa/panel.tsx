"use client";

import { useEffect, useMemo, useOptimistic, useState, useTransition, type FormEvent } from "react";

import { cancelOrderAction, createOrderAction } from "@/app/empresa/actions";
import { formatOrderDate } from "@/lib/demo-orders";
import {
  ORDER_STATUSES,
  addToCart,
  cartQuantity,
  cartTotal,
  type CartItem,
} from "@/lib/orders";
import type {
  AvailableMenu,
  MealSchedule,
  Order,
  ProductionStatus,
  SizeOption,
} from "@/lib/types";

const CURRENCY = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const STATUS_STYLES: Record<ProductionStatus, string> = {
  pending: "bg-amber-50 text-amber-800 ring-amber-200",
  printed: "bg-sky-50 text-sky-800 ring-sky-200",
  separated: "bg-violet-50 text-violet-800 ring-violet-200",
  delivered: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  cancelled: "bg-stone-100 text-stone-600 ring-stone-200",
};

type CompanyPanelProps = {
  company: { id: string; name: string };
  mealSchedules: MealSchedule[];
  cutoffLeadMinutes: number;
  availableMenus: AvailableMenu[];
  initialOrders: Order[];
};

export function CompanyPanel({
  company,
  mealSchedules,
  cutoffLeadMinutes,
  availableMenus,
  initialOrders,
}: CompanyPanelProps) {
  const [orders, updateOrders] = useOptimistic(
    initialOrders,
    (current, update: { kind: "add" | "replace"; order: Order }) =>
      update.kind === "add"
        ? [update.order, ...current]
        : current.map((item) => item.id === update.order.id ? update.order : item),
  );
  const [currentTime, setCurrentTime] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState(availableMenus[0]?.date ?? "");
  const [selectedScheduleId, setSelectedScheduleId] = useState(availableMenus[0]?.available_schedules[0]?.id ?? "");
  const [selectedMenuItem, setSelectedMenuItem] = useState(availableMenus[0]?.items[0]?.id ?? "");
  const [selectedSize, setSelectedSize] = useState<SizeOption>(availableMenus[0]?.items[0]?.size_options[0] ?? "M");
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | ProductionStatus>("all");
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const update = () => setCurrentTime(Date.now());
    const initialUpdate = window.setTimeout(update, 0);
    const interval = window.setInterval(update, 30_000);
    return () => {
      window.clearTimeout(initialUpdate);
      window.clearInterval(interval);
    };
  }, []);

  const activeSchedules = useMemo(
    () => mealSchedules.filter((schedule) => schedule.active).sort(
      (left, right) => left.sort_order - right.sort_order || left.meal_time.localeCompare(right.meal_time),
    ),
    [mealSchedules],
  );
  const currentMenus = useMemo(
    () => currentTime === null ? availableMenus : availableMenus.flatMap((menu) => {
      const available_schedules = menu.available_schedules.filter(
        (schedule) => Date.parse(schedule.cutoff_at) > currentTime,
      );
      return available_schedules.length ? [{ ...menu, available_schedules }] : [];
    }),
    [availableMenus, currentTime],
  );
  const selectedMenu = currentMenus.find((menu) => menu.date === selectedDate) ?? currentMenus[0];
  const effectiveDate = selectedMenu?.date ?? "";
  const selectedDish = selectedMenu?.items.find((item) => item.id === selectedMenuItem) ?? selectedMenu?.items[0];
  const effectiveSize = selectedDish?.size_options.includes(selectedSize) ? selectedSize : selectedDish?.size_options[0];
  const selectedSchedule = selectedMenu?.available_schedules.find((schedule) => schedule.id === selectedScheduleId) ?? selectedMenu?.available_schedules[0];

  const sortedOrders = useMemo(
    () => [...orders].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [orders],
  );
  const filteredOrders = sortedOrders.filter(
    (order) => statusFilter === "all" || order.production_status === statusFilter,
  );
  const activeOrders = orders.filter(
    (order) => !["delivered", "cancelled"].includes(order.production_status),
  ).length;
  const deliveredOrders = orders.filter((order) => order.production_status === "delivered").length;

  function selectDate(date: string) {
    const menu = currentMenus.find((item) => item.date === date);
    setSelectedDate(date);
    setSelectedScheduleId(menu?.available_schedules[0]?.id ?? "");
    setSelectedMenuItem(menu?.items[0]?.id ?? "");
    setSelectedSize(menu?.items[0]?.size_options[0] ?? "M");
    setCart([]);
    setMessage("");
  }

  function addSelectedItem() {
    if (!selectedDish || !effectiveSize || selectedDish.price === null) {
      setMessage("Escolha um prato com preço cadastrado.");
      return;
    }
    const existing = cart.find((item) => item.menu_item_id === selectedDish.id && item.size === effectiveSize);
    if ((existing?.quantity ?? 0) + quantity > 10) {
      setMessage("Cada combinação de prato e tamanho aceita até 10 unidades.");
      return;
    }
    if (cartQuantity(cart) + quantity > 20) {
      setMessage("Um pedido pode conter no máximo 20 marmitas.");
      return;
    }
    if (!existing && cart.length >= 10) {
      setMessage("Um pedido pode conter no máximo 10 itens diferentes.");
      return;
    }
    setCart(addToCart(cart, {
      menu_item_id: selectedDish.id,
      item_name: selectedDish.name,
      size: effectiveSize,
      quantity,
      unit_price: selectedDish.price,
      notes: notes.trim() || null,
    }));
    setQuantity(1);
    setNotes("");
    setMessage(`${selectedDish.name} adicionado ao pedido.`);
  }

  function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const cpf = String(form.get("cpf") ?? "").replace(/\D/g, "");
    const phone = String(form.get("phone") ?? "").replace(/\D/g, "");
    if (!effectiveDate || !selectedSchedule || cart.length === 0) {
      setMessage("Escolha data, horário e adicione ao menos um prato.");
      return;
    }
    if (cpf.length !== 11 || phone.length < 10) {
      setMessage("Confira o CPF e o telefone antes de enviar o pedido.");
      return;
    }

    setMessage("");
    startTransition(async () => {
      const result = await createOrderAction({
        date: effectiveDate,
        meal_schedule_id: selectedSchedule.id,
        employee_name: String(form.get("employeeName") ?? "").trim(),
        employee_phone: phone,
        employee_department: String(form.get("department") ?? "").trim(),
        employee_cpf: cpf,
        employee_internal_id: String(form.get("employeeInternalId") ?? "").trim() || null,
        items: cart.map((item) => ({
          menu_item_id: item.menu_item_id,
          size: item.size,
          quantity: item.quantity,
          notes: item.notes,
        })),
      }, crypto.randomUUID());
      if (result.error || !result.order) {
        setMessage(result.error ?? "Não foi possível criar o pedido.");
        return;
      }
      updateOrders({ kind: "add", order: result.order });
      setCart([]);
      formElement.reset();
      setMessage(`Pedido #${result.order.order_number} criado com sucesso.`);
      window.setTimeout(() => document.querySelector("#pedidos")?.scrollIntoView(), 150);
    });
  }

  function cancel(order: Order) {
    setMessage("");
    startTransition(async () => {
      const result = await cancelOrderAction(order.id);
      if (result.error || !result.order) {
        setMessage(result.error ?? "Não foi possível cancelar o pedido.");
        return;
      }
      updateOrders({ kind: "replace", order: result.order });
      setMessage(`Pedido #${order.order_number} cancelado.`);
    });
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="mb-1 text-sm font-medium text-[#34725f]">{company.name}</p>
          <h1 className="text-2xl font-semibold text-stone-900 sm:text-3xl">Pedidos de refeições</h1>
          <p className="mt-2 text-sm text-stone-600">Monte pedidos com uma ou várias marmitas e acompanhe a produção.</p>
        </div>
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Pedidos encerram <strong>{cutoffLeadMinutes} min antes</strong>
          <p className="mt-1 text-xs">{activeSchedules.length ? activeSchedules.map((schedule) => `${schedule.label} ${schedule.meal_time.slice(0, 5)}`).join(" · ") : "Nenhum horário ativo configurado"}</p>
        </div>
      </header>

      <section className="grid overflow-hidden rounded-md border border-stone-200 bg-white sm:grid-cols-3">
        <Metric label="Pedidos registrados" value={orders.length} />
        <Metric label="Em andamento" value={activeOrders} tone="text-amber-700" />
        <Metric label="Entregues" value={deliveredOrders} tone="text-emerald-700" last />
      </section>

      <section id="novo-pedido" className="scroll-mt-24">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-stone-900">Novo pedido</h2>
          <p className="mt-1 text-sm text-stone-500">O carrinho aceita pratos e tamanhos diferentes para o mesmo funcionário.</p>
        </div>
        <form onSubmit={submitOrder} className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="overflow-hidden rounded-md border border-stone-200 bg-white">
            <div className="grid gap-4 border-b border-stone-200 p-5 sm:grid-cols-2 sm:p-6">
              <label className="text-sm font-medium text-stone-700">
                Data da refeição
                <select value={effectiveDate} disabled={!currentMenus.length} onChange={(event) => selectDate(event.target.value)} className="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2.5 disabled:bg-stone-100">
                  {currentMenus.map((menu) => <option key={menu.date} value={menu.date}>{formatOrderDate(menu.date, true)}</option>)}
                </select>
              </label>
              <label className="text-sm font-medium text-stone-700">
                Horário disponível
                <select value={selectedSchedule?.id ?? ""} disabled={!selectedMenu?.available_schedules.length} onChange={(event) => setSelectedScheduleId(event.target.value)} className="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2.5 disabled:bg-stone-100">
                  {(selectedMenu?.available_schedules ?? []).map((schedule) => <option key={schedule.id} value={schedule.id}>{schedule.label} · {schedule.meal_time.slice(0, 5)} · corte {new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date(schedule.cutoff_at))}</option>)}
                </select>
              </label>
            </div>

            <fieldset className="border-b border-stone-200 p-5 sm:p-6">
              <legend className="mb-4 text-sm font-semibold text-stone-800">Escolha um prato</legend>
              <div className="divide-y divide-stone-100 rounded-md border border-stone-200">
                {selectedMenu?.items.length ? selectedMenu.items.map((item) => (
                  <label key={item.id} className={`flex cursor-pointer items-start gap-3 px-4 py-4 ${selectedDish?.id === item.id ? "bg-emerald-50/70" : "hover:bg-stone-50"}`}>
                    <input type="radio" name="menuItem" checked={selectedDish?.id === item.id} onChange={() => { setSelectedMenuItem(item.id); setSelectedSize(item.size_options[0]); }} className="mt-1 accent-[#216450]" />
                    <span className="min-w-0 flex-1"><strong className="block text-sm text-stone-900">{item.name}</strong><span className="mt-1 block text-sm text-stone-500">{item.description}</span></span>
                    <strong className="text-sm">{item.price === null ? "Sem preço" : CURRENCY.format(item.price)}</strong>
                  </label>
                )) : <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhum cardápio publicado com horário disponível.</p>}
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_120px]">
                <fieldset>
                  <legend className="text-sm font-medium text-stone-700">Tamanho</legend>
                  <div className="mt-2 flex overflow-hidden rounded-md border border-stone-300">
                    {(selectedDish?.size_options ?? []).map((size) => <button key={size} type="button" onClick={() => setSelectedSize(size)} className={`h-10 flex-1 border-r border-stone-300 last:border-0 ${effectiveSize === size ? "bg-[#216450] text-white" : "bg-white"}`}>{size}</button>)}
                  </div>
                </fieldset>
                <label className="text-sm font-medium text-stone-700">Quantidade<input type="number" min={1} max={10} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} className="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label>
              </div>
              <label className="mt-4 block text-sm font-medium text-stone-700">Observação deste item<input value={notes} maxLength={300} onChange={(event) => setNotes(event.target.value)} placeholder="Ex.: sem cebola" className="mt-2 w-full rounded-md border border-stone-300 px-3 py-2.5" /></label>
              <button type="button" onClick={addSelectedItem} disabled={!selectedDish || selectedDish.price === null} className="mt-4 rounded-md border border-[#216450] px-4 py-2.5 text-sm font-semibold text-[#216450] hover:bg-emerald-50 disabled:opacity-40">Adicionar ao pedido</button>
            </fieldset>

            <fieldset className="p-5 sm:p-6">
              <legend className="mb-4 text-sm font-semibold text-stone-800">Dados do colaborador</legend>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field name="employeeName" label="Nome completo" autoComplete="name" />
                <Field name="department" label="Departamento" />
                <Field name="phone" label="Telefone" inputMode="tel" />
                <Field name="cpf" label="CPF" inputMode="numeric" />
                <Field name="employeeInternalId" label="Matrícula (opcional)" required={false} />
              </div>
            </fieldset>
          </div>

          <aside className="rounded-md border border-stone-200 bg-white p-5 xl:sticky xl:top-8">
            <div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase text-stone-500">Resumo</p><span className="text-xs text-stone-500">{cartQuantity(cart)} marmita(s)</span></div>
            <div className="mt-4 divide-y divide-stone-100 border-y border-stone-200">
              {cart.length ? cart.map((item, index) => (
                <div key={`${item.menu_item_id}-${item.size}`} className="py-3">
                  <div className="flex justify-between gap-3 text-sm"><span><strong>{item.quantity}×</strong> {item.item_name} · {item.size}</span><strong>{CURRENCY.format(item.quantity * item.unit_price)}</strong></div>
                  {item.notes ? <p className="mt-1 text-xs text-amber-800">Obs.: {item.notes}</p> : null}
                  <button type="button" onClick={() => setCart((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="mt-1 text-xs text-red-700 hover:underline">Remover</button>
                </div>
              )) : <p className="py-5 text-sm text-stone-500">Adicione um ou mais pratos.</p>}
            </div>
            <dl className="space-y-2 py-4 text-sm">
              <div className="flex justify-between"><dt>Data</dt><dd>{effectiveDate ? formatOrderDate(effectiveDate) : "—"}</dd></div>
              <div className="flex justify-between"><dt>Horário</dt><dd>{selectedSchedule?.meal_time.slice(0, 5) ?? "—"}</dd></div>
              <div className="flex justify-between text-base font-semibold"><dt>Total</dt><dd>{CURRENCY.format(cartTotal(cart))}</dd></div>
            </dl>
            {message ? <p role="status" className="mb-3 rounded-md bg-stone-100 px-3 py-2 text-sm text-stone-700">{message}</p> : null}
            <button type="submit" disabled={isPending || cart.length === 0 || !selectedSchedule} className="w-full rounded-md bg-[#216450] px-4 py-3 text-sm font-semibold text-white hover:bg-[#173f34] disabled:bg-stone-300">{isPending ? "Enviando..." : "Confirmar pedido"}</button>
          </aside>
        </form>
      </section>

      <section id="pedidos" className="scroll-mt-24 pb-8">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div><h2 className="text-lg font-semibold text-stone-900">Pedidos da empresa</h2><p className="mt-1 text-sm text-stone-500">Dados reais salvos pela API.</p></div>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)} className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm"><option value="all">Todos os estados</option>{ORDER_STATUSES.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}</select>
        </div>
        <div className="space-y-3">
          {filteredOrders.length ? filteredOrders.map((order) => {
            const status = ORDER_STATUSES.find((item) => item.value === order.production_status)!;
            const canCancel = order.production_status === "pending" && order.cutoff_at !== null && currentTime !== null && Date.parse(order.cutoff_at) > currentTime;
            return (
              <article key={order.id} className="rounded-md border border-stone-200 bg-white p-4 sm:p-5">
                <div className="flex flex-col justify-between gap-3 sm:flex-row">
                  <div>
                    <div className="flex flex-wrap items-center gap-2"><strong>Pedido #{order.order_number}</strong><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_STYLES[order.production_status]}`}>{status.label}</span></div>
                    <p className="mt-1 text-sm text-stone-500">{formatOrderDate(order.date, true)} · {order.meal_schedule_label ?? "Horário"} {order.scheduled_for ? new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date(order.scheduled_for)) : ""}</p>
                    <p className="mt-1 text-sm text-stone-600">{order.employee_name} · {order.employee_department}</p>
                  </div>
                  <div className="text-left sm:text-right"><strong>{CURRENCY.format(order.total_price)}</strong>{canCancel ? <button type="button" disabled={isPending} onClick={() => cancel(order)} className="mt-2 block text-sm text-red-700 hover:underline sm:ml-auto">Cancelar pedido</button> : null}</div>
                </div>
                <ul className="mt-4 divide-y divide-stone-100 border-t border-stone-100">
                  {order.items.map((item) => <li key={item.id} className="flex justify-between gap-3 py-2 text-sm"><span>{item.quantity}× {item.item_name} · {item.size}{item.notes ? ` · ${item.notes}` : ""}</span><span>{CURRENCY.format(item.subtotal)}</span></li>)}
                </ul>
              </article>
            );
          }) : <p className="rounded-md border border-dashed border-stone-300 bg-white px-4 py-10 text-center text-sm text-stone-500">Nenhum pedido encontrado.</p>}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone = "text-stone-900", last = false }: { label: string; value: number; tone?: string; last?: boolean }) {
  return <div className={`border-b border-stone-200 px-5 py-4 sm:border-b-0 ${last ? "" : "sm:border-r"}`}><p className="text-xs font-medium uppercase text-stone-500">{label}</p><p className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>{value}</p></div>;
}

function Field({ name, label, required = true, ...inputProps }: { name: string; label: string; required?: boolean; autoComplete?: string; inputMode?: "text" | "tel" | "numeric" }) {
  return <label className="text-sm font-medium text-stone-700">{label}<input name={name} required={required} {...inputProps} className="mt-1.5 w-full rounded-md border border-stone-300 px-3 py-2.5 outline-none focus:border-[#34725f] focus:ring-2 focus:ring-emerald-100" /></label>;
}
