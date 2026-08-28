import { PanelShell } from "@/components/panel-shell";
import { requireRole } from "@/lib/auth";

export default async function CompanyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const account = await requireRole("company");

  return (
    <PanelShell
      account={account}
      areaLabel="Portal da empresa"
      nav={[
        { href: "/empresa#novo-pedido", label: "Novo pedido" },
        { href: "/empresa#pedidos", label: "Pedidos da empresa" },
        {
          href: "/empresa/acesso-funcionarios",
          label: "Acesso dos funcionários",
        },
      ]}
    >
      {children}
    </PanelShell>
  );
}
