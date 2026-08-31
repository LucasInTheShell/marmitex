import { PanelShell } from "@/components/panel-shell";
import { requireRole } from "@/lib/auth";

export default async function KitchenLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const account = await requireRole("kitchen");

  return (
    <PanelShell
      account={account}
      areaLabel="Operação da cozinha"
      nav={[
        { href: "/cozinha", label: "Fila de produção" },
        { href: "/cozinha/modo-tv", label: "Modo TV" },
      ]}
    >
      {children}
    </PanelShell>
  );
}
