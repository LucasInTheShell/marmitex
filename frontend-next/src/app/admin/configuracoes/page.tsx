import { OperationalSettingsForm } from "@/app/admin/configuracoes/form";
import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { OperationalSettings } from "@/lib/types";

export default async function OperationalSettingsPage() {
  await requireRole("admin");
  const settings = await apiRequest<OperationalSettings>(
    "/api/v1/operational-settings",
    { token: await sessionToken() },
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold text-stone-800">Configurações</h1>
        <p className="mt-1 text-sm text-stone-500">
          Regras operacionais compartilhadas por todas as empresas.
        </p>
      </header>

      <OperationalSettingsForm
        minutes={settings.order_cutoff_lead_minutes}
      />
    </div>
  );
}
