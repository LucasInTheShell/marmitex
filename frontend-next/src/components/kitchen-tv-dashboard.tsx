"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { localIsoDate, type DemoOrder } from "@/lib/demo-orders";
import { useDemoOrders } from "@/lib/use-demo-orders";
import type { ProductionStatus } from "@/lib/types";

type TvColumn = {
  status: ProductionStatus;
  title: string;
  description: string;
  tone: string;
  header: string;
  empty: string;
};

const TV_COLUMNS: TvColumn[] = [
  {
    status: "pending",
    title: "Aguardando",
    description: "Pedidos recebidos",
    tone: "border-amber-400",
    header: "bg-amber-400 text-amber-950",
    empty: "border-amber-400/25 text-amber-100/60",
  },
  {
    status: "printed",
    title: "Em preparo",
    description: "Produção em andamento",
    tone: "border-sky-400",
    header: "bg-sky-400 text-sky-950",
    empty: "border-sky-400/25 text-sky-100/60",
  },
  {
    status: "separated",
    title: "Prontos",
    description: "Aguardando retirada",
    tone: "border-emerald-400",
    header: "bg-emerald-400 text-emerald-950",
    empty: "border-emerald-400/25 text-emerald-100/60",
  },
];

const CLOCK_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const DATE_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  weekday: "long",
  day: "2-digit",
  month: "long",
});

function minutesSince(createdAt: string, now: Date) {
  return Math.max(0, Math.floor((now.getTime() - new Date(createdAt).getTime()) / 60_000));
}

function elapsedLabel(minutes: number) {
  if (minutes < 1) return "agora";
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `há ${hours}h ${remainder}min` : `há ${hours}h`;
}

function orderNumber(order: DemoOrder) {
  const numeric = order.id.match(/\d+/)?.[0];
  return numeric ? numeric.padStart(3, "0") : order.id.slice(-6).toUpperCase();
}

export function KitchenTvDashboard() {
  const { orders } = useDemoOrders();
  const [now, setNow] = useState(() => new Date());
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const clock = window.setInterval(() => setNow(new Date()), 15_000);
    function syncFullscreen() {
      setFullscreen(Boolean(document.fullscreenElement));
    }
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => {
      window.clearInterval(clock);
      document.removeEventListener("fullscreenchange", syncFullscreen);
    };
  }, []);

  const todayOrders = useMemo(
    () => orders.filter((order) => order.date === localIsoDate() && order.productionStatus !== "delivered"),
    [orders],
  );

  async function toggleFullscreen() {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await document.documentElement.requestFullscreen();
    }
  }

  return (
    <div className="fixed inset-0 z-[70] flex min-h-dvh flex-col overflow-hidden bg-[#071c17] text-white">
      <header className="flex shrink-0 items-center gap-5 border-b border-white/10 bg-[#0c2821] px-5 py-4 2xl:px-8 2xl:py-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-[#e8b44f] text-lg font-black text-[#17372f] 2xl:size-14 2xl:text-2xl">M</span>
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200/70">Mavi Connect</p>
            <h1 className="truncate text-xl font-bold 2xl:text-3xl">Produção em tempo real</h1>
          </div>
        </div>

        <div className="ml-auto hidden items-center gap-3 text-sm lg:flex">
          <span className="flex items-center gap-2 rounded-full bg-emerald-400/10 px-3 py-2 text-emerald-200">
            <span className="size-2.5 animate-pulse rounded-full bg-emerald-400" />
            Atualização automática · mock
          </span>
          <span className="capitalize text-white/65">{DATE_FORMATTER.format(now)}</span>
          <strong className="min-w-24 text-right text-2xl tabular-nums 2xl:text-3xl">{CLOCK_FORMATTER.format(now)}</strong>
        </div>

        <Link href="/cozinha" className="ml-auto rounded-lg border border-white/15 px-3 py-2 text-sm font-semibold text-white/80 hover:bg-white/10 lg:ml-2">
          Voltar à fila
        </Link>
        <button type="button" onClick={toggleFullscreen} className="rounded-lg bg-white px-3 py-2 text-sm font-bold text-[#17372f] hover:bg-emerald-50">
          {fullscreen ? "Sair da tela cheia" : "Tela cheia"}
        </button>
      </header>

      <main className="grid min-h-0 flex-1 gap-3 overflow-x-auto p-3 lg:grid-cols-3 lg:overflow-hidden 2xl:gap-5 2xl:p-5">
        {TV_COLUMNS.map((column) => {
          const columnOrders = todayOrders
            .filter((order) => order.productionStatus === column.status)
            .sort((a, b) => a.createdAt.localeCompare(b.createdAt));

          return (
            <section key={column.status} className={`flex min-h-[420px] min-w-[340px] flex-col overflow-hidden rounded-2xl border ${column.tone} bg-white/[0.045]`}>
              <header className={`flex shrink-0 items-center justify-between px-5 py-4 ${column.header} 2xl:px-6 2xl:py-5`}>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-wide 2xl:text-3xl">{column.title}</h2>
                  <p className="mt-0.5 text-xs font-semibold opacity-70 2xl:text-sm">{column.description}</p>
                </div>
                <span className="grid size-12 place-items-center rounded-full bg-black/10 text-2xl font-black tabular-nums 2xl:size-14 2xl:text-3xl">{columnOrders.length}</span>
              </header>

              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3 2xl:space-y-4 2xl:p-4">
                {columnOrders.length ? columnOrders.map((order) => {
                  const elapsed = minutesSince(order.createdAt, now);
                  const isNew = elapsed <= 12;
                  const isLate = elapsed >= 45 && column.status !== "separated";

                  return (
                    <article key={order.id} className={`relative overflow-hidden rounded-xl border bg-white px-4 py-4 text-stone-950 shadow-xl 2xl:px-5 2xl:py-5 ${isLate ? "border-red-400 ring-2 ring-red-400/50" : isNew ? "border-emerald-400 ring-2 ring-emerald-400/40" : "border-white/20"}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-black uppercase tracking-wide text-stone-500 2xl:text-base">Pedido #{orderNumber(order)}</span>
                            {isNew ? <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-emerald-800 2xl:text-xs">Novo</span> : null}
                            {isLate ? <span className="rounded-full bg-red-100 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-red-800 2xl:text-xs">Atrasado</span> : null}
                          </div>
                          <h3 className="mt-2 truncate text-xl font-black 2xl:text-3xl">{order.employeeName}</h3>
                          <p className="mt-1 truncate text-sm font-bold text-[#216450] 2xl:text-lg">{order.companyName}</p>
                        </div>
                        <span className={`shrink-0 rounded-lg px-3 py-2 text-sm font-black tabular-nums 2xl:text-lg ${isLate ? "bg-red-600 text-white" : "bg-stone-100 text-stone-700"}`}>
                          {elapsedLabel(elapsed)}
                        </span>
                      </div>

                      <div className="my-4 border-y border-stone-200 py-3 2xl:my-5 2xl:py-4">
                        <div className="flex items-center justify-between gap-4">
                          <p className="text-lg font-black 2xl:text-2xl">{order.quantity}× {order.menuItemName}</p>
                          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-stone-900 text-lg font-black text-white 2xl:size-12 2xl:text-xl">{order.size}</span>
                        </div>
                        <p className="mt-2 text-sm font-medium text-stone-500 2xl:text-base">{order.employeeDepartment} · {new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date(order.createdAt))}</p>
                      </div>

                      {order.notes ? <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-950 2xl:text-base"><span className="uppercase">Observação:</span> {order.notes}</p> : null}
                    </article>
                  );
                }) : (
                  <div className={`grid min-h-40 place-items-center rounded-xl border border-dashed px-6 text-center text-lg font-semibold ${column.empty}`}>
                    Nenhum pedido nesta etapa
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}
