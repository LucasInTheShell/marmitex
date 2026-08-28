import { apiRequest } from "@/lib/api/client";
import { requireRole } from "@/lib/auth";
import { sessionToken } from "@/lib/session";
import type { MenuItem } from "@/lib/types";

import { NewMenuItemForm } from "./form";

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
          <ul className="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
            {items.map((item) => (
              <li key={item.id} className="px-5 py-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-stone-800">
                    {item.name}
                  </span>
                  <span className="text-sm text-stone-500">
                    {item.size_options.join(" · ")}
                  </span>
                </div>
                {item.description ? (
                  <p className="mt-1 text-sm text-stone-500">
                    {item.description}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-stone-500">Nenhum prato cadastrado.</p>
        )}
      </section>
    </div>
  );
}
