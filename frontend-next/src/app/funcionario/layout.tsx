import Link from "next/link";

export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-[#f5f6f2] text-stone-900">
      <header className="border-b border-[#cfe2da] bg-white">
        <div className="mx-auto flex min-h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Link href="/funcionario" className="flex items-center gap-3 text-[#17372f]">
            <span className="grid size-10 place-items-center rounded-lg bg-[#e8b44f] font-bold">
              M
            </span>
            <span>
              <span className="block font-semibold leading-tight">Mavi Connect</span>
              <span className="block text-xs text-[#34725f]">Pedidos dos funcionários</span>
            </span>
          </Link>
          <span className="ml-auto hidden rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800 sm:inline-flex">
            Demonstração frontend
          </span>
          <Link
            href="/login"
            className="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Sair
          </Link>
        </div>
      </header>
      {children}
    </div>
  );
}
