import { EmployeeEntry } from "@/components/employee-entry";

export default function EmployeeEntryPage() {
  return (
    <main className="mx-auto grid min-h-[calc(100dvh-65px)] w-full max-w-6xl items-center gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:py-12">
      <section className="hidden rounded-3xl bg-[#17372f] p-10 text-white lg:block">
        <span className="inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-emerald-50">
          Rápido, simples e direto
        </span>
        <h1 className="mt-6 max-w-lg text-4xl font-semibold leading-tight">
          Seu almoço escolhido em poucos passos.
        </h1>
        <p className="mt-4 max-w-lg text-base leading-7 text-emerald-50/75">
          Identifique-se, escolha sua marmita, revise, pague e confirme. A experiência foi pensada primeiro para tablets.
        </p>
        <ol className="mt-10 grid grid-cols-2 gap-3 text-sm">
          {[
            "Identificação",
            "Escolha da marmita",
            "Revisão do pedido",
            "Pagamento",
            "Confirmação",
          ].map((step, index) => (
            <li key={step} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <span className="mb-2 grid size-7 place-items-center rounded-full bg-[#e8b44f] text-xs font-bold text-[#17372f]">
                {index + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
        <span className="inline-flex rounded-full bg-[#eef7f3] px-2.5 py-1 text-xs font-semibold text-[#216450] lg:hidden">
          Ambiente Employee
        </span>
        <h1 className="mt-3 text-2xl font-semibold text-stone-900 sm:text-3xl">
          Acesso dos funcionários
        </h1>
        <p className="mt-2 text-sm leading-6 text-stone-600">
          Entre no ambiente compartilhado da sua empresa para iniciar um novo pedido.
        </p>
        <EmployeeEntry />
      </section>
    </main>
  );
}
