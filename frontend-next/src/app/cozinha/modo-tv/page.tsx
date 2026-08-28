import { KitchenTvDashboard } from "@/components/kitchen-tv-dashboard";
import { requireRole } from "@/lib/auth";

export default async function KitchenTvPage() {
  await requireRole("kitchen");
  return <KitchenTvDashboard />;
}
