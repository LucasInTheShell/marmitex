import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { MenuItem } from "@/lib/types";

import { MenuItemEditor, NewMenuItemForm } from "./form";

export default async function MenuItemsPage() {
  await requireRole("admin");

  const items = await apiRequest<MenuItem[]>("/api/v1/menu-items", {
    token: await sessionToken(),
  });

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold text-stone-800">Pratos</h1>

      <NewMenuItemForm />

      <section>
        <h2 className="mb-3 font-medium text-stone-800">Pratos cadastrados</h2>

        {items.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {items.map((item) => (
              <MenuItemEditor key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-stone-500">Nenhum prato cadastrado.</p>
        )}
      </section>
    </div>
  );
}
