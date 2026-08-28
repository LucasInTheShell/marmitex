"use client";

import Link from "next/link";
import { useState } from "react";

import { DEMO_MENU_ITEMS, type DemoMenuItem } from "@/lib/demo-orders";

type Step = "identification" | "menu" | "details" | "review" | "success";
type OrderDraft = {
  employeeName: string;
  department: string;
  internalId: string;
  dish: DemoMenuItem | null;
  size: "P" | "M" | "G";
  quantity: number;
  notes: string;
};

const STEP_LABELS = ["Identificação", "Cardápio", "Detalhes", "Revisão"];
const DISH_META: Record<string, { accompaniment: string; availability: string }> = {
  "frango-grelhado": { accompaniment: "Salada fresca e legumes", availability: "Disponível" },
  "picadinho-carne": { accompaniment: "Farofa e couve refogada", availability: "Últimas unidades" },
  vegetariano: { accompaniment: "Molho de ervas", availability: "Disponível" },
};

export function EmployeeOrderFlow() {
  const [step, setStep] = useState<Step>("identification");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draft, setDraft] = useState<OrderDraft>({
    employeeName: "",
    department: "",
    internalId: "",
    dish: null,
    size: "M",
    quantity: 1,
    notes: "",
  });

  const currentStep = {
    identification: 0,
    menu: 1,
    details: 2,
    review: 3,
    success: 4,
  }[step];

  function identify(formData: FormData) {
    const employeeName = String(formData.get("employeeName") ?? "").trim();
    const department = String(formData.get("department") ?? "").trim();
    const internalId = String(formData.get("internalId") ?? "").trim();

    if (employeeName.length < 3 || department.length < 2) {
      setError("Informe seu nome completo e setor para continuar.");
      return;
    }

    setDraft((current) => ({ ...current, employeeName, department, internalId }));
    setError(null);
    setStep("menu");
  }

  function selectDish(dish: DemoMenuItem) {
    setDraft((current) => ({ ...current, dish }));
    setStep("details");
    setError(null);
  }

  function review(formData: FormData) {
    const notes = String(formData.get("notes") ?? "").trim();
    setDraft((current) => ({ ...current, notes }));
    setStep("review");
  }

  function confirm() {
    setSubmitting(true);
    window.setTimeout(() => {
      setSubmitting(false);
      setStep("success");
    }, 700);
  }

  function restart() {
    setDraft({
      employeeName: "",
      department: "",
      internalId: "",
      dish: null,
      size: "M",
      quantity: 1,
      notes: "",
    });
    setError(null);
    setStep("identification");
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
      {step !== "success" ? (
        <ol className="mb-6 grid grid-cols-4 gap-1 sm:mb-8 sm:gap-3" aria-label="Etapas do pedido">
          {STEP_LABELS.map((label, index) => (
            <li key={label} className="min-w-0">
              <div className={`h-1.5 rounded-full ${index <= currentStep ? "bg-[#216450]" : "bg-stone-200"}`} />
              <span className={`mt-2 block truncate text-[11px] font-medium sm:text-sm ${index === currentStep ? "text-[#216450]" : "text-stone-500"}`}>
                {index + 1}. {label}
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      {step === "identification" ? (
        <StepCard
          eyebrow="Passo 1 de 4"
          title="Quem está fazendo o pedido?"
          description="A conta é compartilhada pela empresa, então precisamos identificar cada funcionário."
        >
          <form action={identify} className="mt-6 grid gap-5 sm:grid-cols-2">
            <TouchInput name="employeeName" label="Nome completo" placeholder="Ex.: Maria da Silva" autoFocus />
            <TouchInput name="department" label="Setor" placeholder="Ex.: Financeiro" />
            <TouchInput name="internalId" label="Matrícula (opcional)" placeholder="Ex.: 1042" />
            <div className="flex items-end">
              <button type="submit" className="min-h-14 w-full rounded-xl bg-[#216450] px-5 text-base font-semibold text-white hover:bg-[#173f34]">
                Ver cardápio
              </button>
            </div>
            {error ? <p role="alert" className="text-sm font-medium text-red-600 sm:col-span-2">{error}</p> : null}
          </form>
        </StepCard>
      ) : null}

      {step === "menu" ? (
        <section>
          <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-semibold text-[#34725f]">Olá, {draft.employeeName}</p>
              <h1 className="mt-1 text-2xl font-semibold text-stone-900 sm:text-3xl">Escolha sua marmita</h1>
              <p className="mt-2 text-sm text-stone-600">Cardápio demonstrativo de hoje · 28 de agosto</p>
            </div>
            <button type="button" onClick={() => setStep("identification")} className="text-left text-sm font-semibold text-[#216450] hover:underline">
              Alterar identificação
            </button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {DEMO_MENU_ITEMS.map((dish, index) => (
              <button
                key={dish.id}
                type="button"
                onClick={() => selectDish(dish)}
                className="group overflow-hidden rounded-2xl border border-stone-200 bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:border-[#79a995] hover:shadow-md focus:outline-none focus:ring-4 focus:ring-emerald-100"
              >
                <div className={`relative h-40 ${dish.accent}`}>
                  <div className="absolute inset-0 bg-gradient-to-br from-white/25 to-stone-950/20" />
                  <span className="absolute left-4 top-4 rounded-full bg-white/90 px-2.5 py-1 text-xs font-semibold text-[#17372f]">
                    {DISH_META[dish.id].availability}
                  </span>
                  <span className="absolute bottom-4 right-4 text-6xl font-black text-white/30">0{index + 1}</span>
                </div>
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <h2 className="text-lg font-semibold text-stone-900">{dish.name}</h2>
                    <span className="shrink-0 font-semibold text-[#216450]">R$ {dish.price.toFixed(2).replace(".", ",")}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-stone-600">{dish.description}</p>
                  <p className="mt-3 text-xs font-medium text-stone-500">Acompanha: {DISH_META[dish.id].accompaniment}</p>
                  <span className="mt-5 block min-h-12 rounded-xl bg-[#eef7f3] px-4 py-3 text-center text-sm font-semibold text-[#216450] group-hover:bg-[#216450] group-hover:text-white">
                    Ver detalhes
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {step === "details" && draft.dish ? (
        <StepCard
          eyebrow="Passo 3 de 4"
          title={draft.dish.name}
          description={draft.dish.description}
          back={() => setStep("menu")}
        >
          <form action={review} className="mt-7 grid gap-7 lg:grid-cols-[1fr_320px]">
            <div className="space-y-7">
              <fieldset>
                <legend className="text-sm font-semibold text-stone-800">Escolha o tamanho</legend>
                <div className="mt-3 grid grid-cols-3 gap-3">
                  {(["P", "M", "G"] as const).map((size) => (
                    <button
                      key={size}
                      type="button"
                      aria-pressed={draft.size === size}
                      onClick={() => setDraft((current) => ({ ...current, size }))}
                      className={`min-h-14 rounded-xl border text-base font-bold ${draft.size === size ? "border-[#216450] bg-[#216450] text-white" : "border-stone-300 bg-white text-stone-700 hover:bg-stone-50"}`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </fieldset>

              <div>
                <p className="text-sm font-semibold text-stone-800">Quantidade</p>
                <div className="mt-3 flex w-fit items-center overflow-hidden rounded-xl border border-stone-300 bg-white">
                  <button type="button" aria-label="Diminuir quantidade" onClick={() => setDraft((current) => ({ ...current, quantity: Math.max(1, current.quantity - 1) }))} className="grid size-14 place-items-center text-2xl text-stone-600 hover:bg-stone-50">−</button>
                  <output className="grid h-14 min-w-16 place-items-center border-x border-stone-300 text-lg font-bold">{draft.quantity}</output>
                  <button type="button" aria-label="Aumentar quantidade" onClick={() => setDraft((current) => ({ ...current, quantity: Math.min(5, current.quantity + 1) }))} className="grid size-14 place-items-center text-2xl text-stone-600 hover:bg-stone-50">+</button>
                </div>
              </div>

              <label className="block text-sm font-semibold text-stone-800">
                Observações (opcional)
                <textarea name="notes" rows={4} maxLength={180} placeholder="Ex.: sem cebola" className="mt-2 w-full rounded-xl border border-stone-300 px-4 py-3 font-normal outline-none placeholder:text-stone-400 focus:border-[#34725f] focus:ring-4 focus:ring-emerald-100" />
              </label>
            </div>

            <aside className="rounded-2xl bg-[#eef7f3] p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#34725f]">Sua escolha</p>
              <p className="mt-3 text-xl font-semibold text-[#17372f]">{draft.dish.name}</p>
              <p className="mt-2 text-sm leading-6 text-[#34725f]">{DISH_META[draft.dish.id].accompaniment}</p>
              <div className="my-5 border-t border-[#cfe2da]" />
              <p className="text-sm text-[#34725f]">A partir de</p>
              <p className="mt-1 text-2xl font-semibold text-[#17372f]">R$ {draft.dish.price.toFixed(2).replace(".", ",")}</p>
              <button type="submit" className="mt-6 min-h-14 w-full rounded-xl bg-[#216450] px-5 text-base font-semibold text-white hover:bg-[#173f34]">
                Revisar pedido
              </button>
            </aside>
          </form>
        </StepCard>
      ) : null}

      {step === "review" && draft.dish ? (
        <StepCard
          eyebrow="Passo 4 de 4"
          title="Revise antes de confirmar"
          description="Confira os dados abaixo. Nesta demonstração, o pedido não será enviado nem persistido."
          back={() => setStep("details")}
        >
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            <ReviewSection title="Funcionário">
              <ReviewRow label="Nome" value={draft.employeeName} />
              <ReviewRow label="Setor" value={draft.department} />
              {draft.internalId ? <ReviewRow label="Matrícula" value={draft.internalId} /> : null}
            </ReviewSection>
            <ReviewSection title="Pedido">
              <ReviewRow label="Marmita" value={draft.dish.name} />
              <ReviewRow label="Tamanho" value={draft.size} />
              <ReviewRow label="Quantidade" value={String(draft.quantity)} />
              <ReviewRow label="Observações" value={draft.notes || "Nenhuma"} />
            </ReviewSection>
          </div>
          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button type="button" onClick={() => setStep("details")} className="min-h-14 rounded-xl border border-stone-300 px-5 text-base font-semibold text-stone-700 hover:bg-stone-50">Editar pedido</button>
            <button type="button" onClick={confirm} disabled={submitting} className="min-h-14 rounded-xl bg-[#216450] px-6 text-base font-semibold text-white hover:bg-[#173f34] disabled:cursor-wait disabled:opacity-70">
              {submitting ? "Confirmando…" : "Confirmar pedido"}
            </button>
          </div>
        </StepCard>
      ) : null}

      {step === "success" ? (
        <section className="mx-auto max-w-2xl rounded-3xl border border-emerald-200 bg-white px-6 py-12 text-center shadow-sm sm:px-10">
          <span className="mx-auto grid size-20 place-items-center rounded-full bg-emerald-100 text-4xl text-emerald-700">✓</span>
          <p className="mt-6 text-sm font-semibold uppercase tracking-wide text-emerald-700">Demonstração concluída</p>
          <h1 className="mt-2 text-3xl font-semibold text-stone-900">Pedido realizado!</h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-stone-600">
            Obrigado, {draft.employeeName}. Seu pedido de {draft.quantity}× {draft.dish?.name} foi simulado com sucesso.
          </p>
          <div className="mx-auto mt-7 max-w-sm rounded-xl bg-stone-50 px-5 py-4 text-left text-sm">
            <ReviewRow label="Protocolo" value="#DEMO-0828" />
            <ReviewRow label="Status" value="Não enviado ao backend" />
          </div>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <button type="button" onClick={restart} className="min-h-14 rounded-xl bg-[#216450] px-6 text-base font-semibold text-white hover:bg-[#173f34]">Fazer outro pedido</button>
            <Link href="/funcionario" className="grid min-h-14 place-items-center rounded-xl border border-stone-300 px-6 text-base font-semibold text-stone-700 hover:bg-stone-50">Voltar ao acesso</Link>
          </div>
        </section>
      ) : null}
    </main>
  );
}

function StepCard({
  eyebrow,
  title,
  description,
  back,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  back?: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-8">
      <div className="flex items-start gap-4">
        {back ? (
          <button type="button" onClick={back} aria-label="Voltar" className="grid size-11 shrink-0 place-items-center rounded-xl border border-stone-300 text-xl text-stone-600 hover:bg-stone-50">←</button>
        ) : null}
        <div>
          <p className="text-sm font-semibold text-[#34725f]">{eyebrow}</p>
          <h1 className="mt-1 text-2xl font-semibold text-stone-900 sm:text-3xl">{title}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function TouchInput({
  name,
  label,
  placeholder,
  autoFocus = false,
}: {
  name: string;
  label: string;
  placeholder: string;
  autoFocus?: boolean;
}) {
  return (
    <label className="text-sm font-semibold text-stone-700">
      {label}
      <input name={name} autoFocus={autoFocus} placeholder={placeholder} className="mt-2 min-h-14 w-full rounded-xl border border-stone-300 px-4 text-base font-normal outline-none placeholder:text-stone-400 focus:border-[#34725f] focus:ring-4 focus:ring-emerald-100" />
    </label>
  );
}

function ReviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-stone-50 p-5">
      <h2 className="mb-4 font-semibold text-stone-900">{title}</h2>
      <dl className="space-y-3">{children}</dl>
    </section>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-stone-200 pb-2 last:border-0 last:pb-0">
      <dt className="text-stone-500">{label}</dt>
      <dd className="text-right font-semibold text-stone-800">{value}</dd>
    </div>
  );
}
