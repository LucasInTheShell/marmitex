"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { signOut } from "@/app/login/actions";

type PanelShellProps = {
  account: { name: string; email: string };
  areaLabel: string;
  nav: Array<{ href: string; label: string }>;
  children: React.ReactNode;
};

type SidebarContentProps = Pick<PanelShellProps, "account" | "areaLabel" | "nav"> & {
  pathname: string;
  collapsed: boolean;
  mobile?: boolean;
  onCloseMobile: () => void;
  onToggleCollapsed: () => void;
};

function SidebarContent({
  account,
  areaLabel,
  nav,
  pathname,
  collapsed,
  mobile = false,
  onCloseMobile,
  onToggleCollapsed,
}: SidebarContentProps) {
  const compact = collapsed && !mobile;

  return (
    <>
      <div
        className={`flex items-center border-b border-white/10 ${compact ? "justify-center px-3 py-5" : "gap-3 px-6 py-5"}`}
      >
        <Link
          href="/"
          className="flex min-w-0 flex-1 items-center gap-3"
          onClick={onCloseMobile}
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-[#e8b44f] font-bold text-[#17372f]">
            M
          </span>
          {!compact ? (
            <span className="min-w-0">
              <span className="block truncate font-semibold leading-tight">
                Mavi Connect
              </span>
              <span className="block truncate text-xs text-emerald-100/70">
                {areaLabel}
              </span>
            </span>
          ) : null}
        </Link>

        {!mobile ? (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
            aria-expanded={!collapsed}
            className="hidden size-8 shrink-0 place-items-center rounded-md border border-white/10 text-emerald-50/75 hover:bg-white/10 hover:text-white md:grid"
          >
            <ChevronIcon direction={collapsed ? "right" : "left"} />
          </button>
        ) : (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Fechar menu"
            className="grid size-8 shrink-0 place-items-center rounded-md border border-white/10 text-emerald-50/75"
          >
            ×
          </button>
        )}
      </div>

      <nav
        className={`flex-1 space-y-1 py-5 ${compact ? "px-2" : "px-3"}`}
        aria-label="Navegação principal"
      >
        {nav.map((item) => {
          const routePath = item.href.split("#")[0];
          const active =
            pathname === routePath ||
            (routePath !== "/" && pathname.startsWith(`${routePath}/`));

          return (
            <Link
              key={item.href}
              href={item.href}
              title={compact ? item.label : undefined}
              aria-current={active ? "page" : undefined}
              onClick={onCloseMobile}
              className={`flex min-h-11 items-center rounded-md text-sm transition-colors ${
                compact ? "justify-center px-2" : "gap-3 px-3"
              } ${
                active
                  ? "bg-white/12 font-medium text-white"
                  : "text-emerald-50/75 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span
                className={`grid size-7 shrink-0 place-items-center rounded text-xs font-bold ${
                  active ? "bg-[#e8b44f] text-[#17372f]" : "bg-white/8"
                }`}
                aria-hidden="true"
              >
                {item.label.slice(0, 1).toLocaleUpperCase("pt-BR")}
              </span>
              {!compact ? <span className="truncate">{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div className={`border-t border-white/10 ${compact ? "p-2" : "p-4"}`}>
        {!compact ? (
          <>
            <p className="truncate text-sm font-medium">{account.name}</p>
            <p className="mb-3 truncate text-xs text-emerald-100/60">
              {account.email}
            </p>
          </>
        ) : null}
        <form action={signOut}>
          <button
            type="submit"
            title={compact ? "Sair da conta" : undefined}
            className={`rounded-md border border-white/15 py-2 text-sm text-emerald-50/80 hover:bg-white/5 hover:text-white ${
              compact ? "w-full px-2 text-center" : "w-full px-3 text-left"
            }`}
          >
            {compact ? "↪" : "Sair da conta"}
          </button>
        </form>
      </div>
    </>
  );
}

export function PanelShell({ account, areaLabel, nav, children }: PanelShellProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-[#f5f6f2] text-stone-900">
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-[#28453b] bg-[#17372f] text-white transition-[width] duration-200 md:flex ${
          collapsed ? "w-20" : "w-64"
        }`}
      >
        <SidebarContent
          account={account}
          areaLabel={areaLabel}
          nav={nav}
          pathname={pathname}
          collapsed={collapsed}
          onCloseMobile={() => setMobileOpen(false)}
          onToggleCollapsed={() => setCollapsed((current) => !current)}
        />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Fechar menu"
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-stone-950/45"
          />
          <aside className="relative flex h-full w-[min(82vw,320px)] flex-col border-r border-[#28453b] bg-[#17372f] text-white shadow-2xl">
            <SidebarContent
              account={account}
              areaLabel={areaLabel}
              nav={nav}
              pathname={pathname}
              collapsed={collapsed}
              mobile
              onCloseMobile={() => setMobileOpen(false)}
              onToggleCollapsed={() => setCollapsed((current) => !current)}
            />
          </aside>
        </div>
      ) : null}

      <div
        className={`transition-[padding] duration-200 ${collapsed ? "md:pl-20" : "md:pl-64"}`}
      >
        <header className="sticky top-0 z-20 flex h-16 items-center border-b border-stone-200 bg-white/95 px-4 backdrop-blur md:hidden">
          <button
            type="button"
            aria-label="Abrir menu"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(true)}
            className="mr-3 grid size-9 place-items-center rounded-md border border-stone-200 text-[#17372f]"
          >
            <MenuIcon />
          </button>
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

function ChevronIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={`size-4 ${direction === "right" ? "rotate-180" : ""}`}
      aria-hidden="true"
    >
      <path
        d="m12.5 4.5-5 5.5 5 5.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="size-5" aria-hidden="true">
      <path
        d="M3 5.5h14M3 10h14M3 14.5h14"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
