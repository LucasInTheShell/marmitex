/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";

import { paymentLabel, pixControls } from "@/lib/orders";
import type { Order, PixCheckout } from "@/lib/types";

type PixPaymentPanelProps = {
  checkout: PixCheckout;
  order: Order;
  statusUrl: string;
  onOrderUpdated: (order: Order) => void;
  onSwitchToDelivery: () => Promise<Order | null>;
};

export function PixPaymentPanel({
  checkout, order, statusUrl, onOrderUpdated, onSwitchToDelivery,
}: PixPaymentPanelProps) {
  const [message, setMessage] = useState("");
  const [switching, setSwitching] = useState(false);
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (order.payment_method !== "pix" || ["paid", "refunded", "cancelled"].includes(order.payment_status)) return;
    let active = true;
    let running = false;
    const controller = new AbortController();
    const poll = async () => {
      if (running) return;
      running = true;
      try {
        const response = await fetch(statusUrl, { cache: "no-store", signal: controller.signal });
        if (response.ok && active) onOrderUpdated((await response.json()) as Order);
      } catch {
        // Poll only our backend; provider reconciliation is server-side.
      } finally {
        running = false;
      }
    };
    const interval = window.setInterval(poll, 4_000);
    return () => { active = false; controller.abort(); window.clearInterval(interval); };
  }, [onOrderUpdated, order.payment_method, order.payment_status, statusUrl]);

  const { beforeCutoff, canPay, canSwitch } = pixControls(order, checkout.expires_at, now);
  const paid = order.payment_status === "paid";
  const processing = order.payment_status === "processing";
  const review = order.payment_status === "review_required";

  async function copyCode() {
    if (!canPay || Date.now() >= new Date(checkout.expires_at).getTime()) return;
    try {
      await navigator.clipboard.writeText(checkout.pix_copy_paste);
      setMessage("Código Pix copiado.");
    } catch {
      setMessage("Não foi possível copiar automaticamente. Selecione o código e copie manualmente.");
    }
  }

  async function switchToDelivery() {
    setSwitching(true);
    setMessage("");
    try {
      const updated = await onSwitchToDelivery();
      if (!updated) throw new Error("Não foi possível alterar. O pagamento pode já estar confirmado.");
      onOrderUpdated(updated);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível alterar a forma de pagamento.");
    } finally {
      setSwitching(false);
    }
  }

  return (
    <section className="rounded-2xl border border-emerald-200 bg-white p-5 shadow-sm sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#34725f]">Pedido #{order.order_number}</p>
      <h2 className="mt-1 text-xl font-semibold text-stone-900">{paid ? "Pix confirmado" : "Pagamento via Pix"}</h2>
      <p className="mt-2 text-sm text-stone-600">
        {paymentLabel(order.payment_method, order.payment_status)} · { (checkout.amount_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: checkout.currency.toUpperCase() })}
      </p>
      {paid && <p className="mt-6 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">Pagamento confirmado. O pedido foi liberado para a cozinha.</p>}
      {review && <p role="alert" className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Este pagamento precisa de análise da empresa, por confirmação fora do prazo ou divergência financeira. O pedido não foi liberado automaticamente. Não faça outro pagamento; entre em contato com o responsável.</p>}
      {processing && <p className="mt-6 text-sm text-amber-800">Confirmando o pagamento. Aguarde; não faça outro Pix e não altere a forma de pagamento.</p>}
      {canPay && checkout.qr_code_base64 && checkout.pix_copy_paste && (
        <div className="mt-6 grid gap-5 md:grid-cols-[220px_1fr] md:items-center">
          <div className="grid min-h-[220px] place-items-center rounded-xl border border-stone-200 bg-white p-3">
            <img src={`data:image/png;base64,${checkout.qr_code_base64}`} alt="QR Code para pagamento via Pix" className="size-48" />
          </div>
          <div>
            <label className="text-sm font-semibold text-stone-800">Pix copia e cola
              <textarea readOnly value={checkout.pix_copy_paste} rows={5} className="mt-2 w-full resize-none rounded-xl border border-stone-300 bg-stone-50 p-3 text-xs" />
            </label>
            <button type="button" onClick={copyCode} className="mt-3 min-h-11 rounded-xl border border-[#216450] px-4 text-sm font-semibold text-[#216450]">Copiar código Pix</button>
          </div>
        </div>
      )}
      {!paid && !review && !processing && now !== null && !beforeCutoff && (
        <p className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Prazo encerrado. Não pague um código copiado anteriormente. Se já pagou, aguarde a confirmação ou entre em contato com a empresa.</p>
      )}
      {!paid && <p className="mt-4 text-xs text-stone-500">Prazo para pagar: {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(checkout.expires_at))}.</p>}
      {canSwitch && <button type="button" onClick={switchToDelivery} disabled={switching} className="mt-4 text-sm font-semibold text-[#216450] hover:underline disabled:opacity-60">{switching ? "Alterando…" : "Prefiro pagar na entrega"}</button>}
      {message && <p role="status" className="mt-4 rounded-xl bg-stone-100 px-4 py-3 text-sm text-stone-700">{message}</p>}
    </section>
  );
}
