import Link from "next/link";

import { signOut } from "@/app/login/actions";
import { requireRole } from "@/lib/auth";

const NAV = [
  { href: "/admin/empresas", label: "Empresas" },
  { href: "/admin/pratos", label: "Pratos" },
  { href: "/admin/cardapio", label: "Cardápio da semana" },
];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const account = await requireRole("admin");

  return (
    <div className="min-h-dvh bg-stone-50">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
          <span className="font-semibold text-stone-800">Mavi Connect</span>
          <nav className="flex gap-4 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-stone-600 hover:text-stone-900"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <form action={signOut} className="ml-auto">
            <span className="mr-3 text-sm text-stone-500">{account.email}</span>
            <button
              type="submit"
              className="text-sm text-stone-600 underline hover:text-stone-900"
            >
              Sair
            </button>
          </form>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
