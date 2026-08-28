import { PanelShell } from "@/components/panel-shell";
import { requireRole } from "@/lib/auth";

const NAV = [
  { href: "/admin/empresas", label: "Empresas" },
  { href: "/admin/usuarios", label: "Usuários" },
  { href: "/admin/acessos-funcionarios", label: "Acessos Employee" },
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
    <PanelShell account={account} areaLabel="Administração" nav={NAV}>
      {children}
    </PanelShell>
  );
}
