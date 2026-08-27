import Link from "next/link";

import { signOut } from "@/app/login/actions";

type PanelShellProps = {
  account: { name: string; email: string };
  areaLabel: string;
  nav: Array<{ href: string; label: string }>;
  children: React.ReactNode;
};

export function PanelShell({
  account,
  areaLabel,
  nav,
  children,
}: PanelShellProps) {
  return (
    <div className="min-h-dvh bg-[#f5f6f2] text-stone-900">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-[#28453b] bg-[#17372f] text-white md:flex">
        <div className="border-b border-white/10 px-6 py-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-md bg-[#e8b44f] font-bold text-[#17372f]">
              M
            </span>
            <span>
              <span className="block font-semibold leading-tight">Mavi Connect</span>
              <span className="block text-xs text-emerald-100/70">{areaLabel}</span>
            </span>
          </Link>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Navegação principal">
          {nav.map((item, index) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-md px-3 py-2.5 text-sm transition-colors ${
                index === 0
                  ? "bg-white/10 font-medium text-white"
                  : "text-emerald-50/75 hover:bg-white/5 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <p className="truncate text-sm font-medium">{account.name}</p>
          <p className="mb-3 truncate text-xs text-emerald-100/60">{account.email}</p>
          <form action={signOut}>
            <button
              type="submit"
              className="w-full rounded-md border border-white/15 px-3 py-2 text-left text-sm text-emerald-50/80 hover:bg-white/5 hover:text-white"
            >
              Sair da conta
            </button>
          </form>
        </div>
      </aside>

      <div className="md:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center border-b border-stone-200 bg-white/95 px-4 backdrop-blur md:hidden">
          <Link href="/" className="flex items-center gap-2 font-semibold text-[#17372f]">
            <span className="grid size-8 place-items-center rounded-md bg-[#e8b44f] text-sm font-bold">
              M
            </span>
            Mavi Connect
          </Link>
          <form action={signOut} className="ml-auto">
            <button type="submit" className="text-sm font-medium text-stone-600">
              Sair
            </button>
          </form>
        </header>

        <main className="mx-auto w-full max-w-[1480px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
