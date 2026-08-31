"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { formatMealTime } from "@/lib/orders";
import type { KitchenOrder, KitchenProductionStatus } from "@/lib/types";

const COLUMNS: Array<{
  status: Extract<KitchenProductionStatus, "pending" | "printed" | "separated">;
  title: string;
  description: string;
  tone: string;
  header: string;
  empty: string;
}> = [
  { status: "pending", title: "Recebidos", description: "Aguardando impressão", tone: "border-amber-400/50", header: "bg-amber-400 text-amber-950", empty: "border-amber-300/40 text-amber-100/70" },
  { status: "printed", title: "Em produção", description: "Comanda impressa", tone: "border-sky-400/50", header: "bg-sky-400 text-sky-950", empty: "border-sky-300/40 text-sky-100/70" },
  { status: "separated", title: "Prontos", description: "Aguardando entrega", tone: "border-emerald-400/50", header: "bg-emerald-400 text-emerald-950", empty: "border-emerald-300/40 text-emerald-100/70" },
];

function minutesSince(isoDate: string, now: number) {
  return Math.max(0, Math.floor((now - Date.parse(isoDate)) / 60_000));
}

function elapsedLabel(minutes: number) {
  if (minutes < 1) return "agora";
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`;
}

export function KitchenTvDashboard({ initialOrders, date }: { initialOrders: KitchenOrder[]; date: string }) {
  const router = useRouter();
  const [now, setNow] = useState<number | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const dashboardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const updateClock = () => setNow(Date.now());
    const initialClock = window.setTimeout(updateClock, 0);
    const clock = window.setInterval(updateClock, 30_000);
    const refresh = window.setInterval(() => router.refresh(), 20_000);
    const syncFullscreen = () => setFullscreen(document.fullscreenElement === dashboardRef.current);
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => {
      window.clearTimeout(initialClock);
      window.clearInterval(clock);
      window.clearInterval(refresh);
      document.removeEventListener("fullscreenchange", syncFullscreen);
    };
  }, [router]);

  async function toggleFullscreen() {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await dashboardRef.current?.requestFullscreen();
  }

  const activeOrders = initialOrders.filter((order) => order.production_status !== "delivered");
  const totalMeals = activeOrders.reduce(
    (total, order) => total + order.items.reduce((subtotal, item) => subtotal + item.quantity, 0),
    0,
  );

  return (
    <div ref={dashboardRef} className="flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden rounded-2xl bg-[#102e27] p-4 text-white sm:p-5 2xl:p-7">
      <header className="mb-5 flex shrink-0 flex-wrap items-end justify-between gap-4 border-b border-white/15 pb-5">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-300">Mavi Connect · Modo TV</p>
          <h1 className="mt-1 text-3xl font-black sm:text-4xl 2xl:text-5xl">Fila de produção</h1>
          <p className="mt-2 text-sm text-emerald-100/70">{new Intl.DateTimeFormat("pt-BR", { dateStyle: "full" }).format(new Date(`${date}T12:00:00`))} · sincronização a cada 20 s</p>
        </div>
        <div className="flex flex-wrap justify-end gap-3">
          <TvMetric label="Pedidos ativos" value={activeOrders.length} />
          <TvMetric label="Marmitas" value={totalMeals} />
          <TvMetric label="Prontos" value={activeOrders.filter((order) => order.production_status === "separated").length} />
          <button type="button" onClick={toggleFullscreen} className="rounded-xl bg-white px-4 py-3 text-sm font-bold text-[#17372f]">{fullscreen ? "Sair da tela cheia" : "Tela cheia"}</button>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-x-auto lg:grid-cols-3">
        {COLUMNS.map((column) => {
          const columnOrders = activeOrders
            .filter((order) => order.production_status === column.status)
            .sort((left, right) => (left.scheduled_for ?? "").localeCompare(right.scheduled_for ?? "") || left.created_at.localeCompare(right.created_at));
          return (
            <section key={column.status} className={`flex min-h-[420px] min-w-[340px] flex-col overflow-hidden rounded-2xl border ${column.tone} bg-white/[0.045]`}>
              <header className={`flex items-center justify-between px-5 py-4 ${column.header}`}>
                <div><h2 className="text-xl font-black uppercase tracking-wide 2xl:text-3xl">{column.title}</h2><p className="text-xs font-semibold opacity-70 2xl:text-sm">{column.description}</p></div>
                <span className="grid size-12 place-items-center rounded-full bg-black/10 text-2xl font-black">{columnOrders.length}</span>
              </header>
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
                {columnOrders.length ? columnOrders.map((order) => {
                  const elapsed = now === null ? 0 : minutesSince(order.created_at, now);
                  const isNew = elapsed <= 12;
                  const isLate = elapsed >= 45 && column.status !== "separated";
                  return (
                    <article key={order.id} className={`rounded-xl border bg-white px-4 py-4 text-stone-950 shadow-xl ${isLate ? "border-red-400 ring-2 ring-red-400/50" : isNew ? "border-emerald-400 ring-2 ring-emerald-400/40" : "border-white/20"}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0"><p className="text-sm font-black uppercase tracking-wide text-stone-500">Pedido #{order.order_number} · almoço {formatMealTime(order.scheduled_for)}</p><h3 className="mt-2 truncate text-xl font-black 2xl:text-3xl">{order.employee_name}</h3><p className="mt-1 truncate text-sm font-bold text-[#216450] 2xl:text-lg">{order.company_name}</p></div>
                        <span className={`shrink-0 rounded-lg px-3 py-2 text-sm font-black ${isLate ? "bg-red-600 text-white" : "bg-stone-100 text-stone-700"}`}>{elapsedLabel(elapsed)}</span>
                      </div>
                      <ul className="my-4 divide-y divide-stone-200 border-y border-stone-200">
                        {order.items.map((item) => <li key={item.id} className="py-3"><p className="text-lg font-black 2xl:text-2xl">{item.quantity}× {item.item_name} <span className="rounded bg-stone-900 px-2 py-1 text-sm text-white">{item.size}</span></p>{item.notes ? <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm font-bold text-amber-950">OBS: {item.notes}</p> : null}</li>)}
                      </ul>
                      <p className="text-sm font-medium text-stone-500">{order.employee_department}</p>
                    </article>
                  );
                }) : <div className={`grid min-h-40 place-items-center rounded-xl border border-dashed px-6 text-center text-lg font-semibold ${column.empty}`}>Nenhum pedido nesta etapa</div>}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}

function TvMetric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-center"><strong className="block text-2xl font-black tabular-nums">{value}</strong><span className="text-xs font-semibold text-emerald-100/70">{label}</span></div>;
}
