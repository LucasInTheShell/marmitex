import { KitchenPanel } from "@/app/cozinha/panel";
import { requireRole } from "@/lib/auth";

export default async function KitchenPage() {
  await requireRole("kitchen");
  return <KitchenPanel />;
}
