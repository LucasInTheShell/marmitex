import type {
  KitchenProductionStatus,
  MenuItem,
  OrderCreateItem,
  ProductionStatus,
} from "@/lib/types";

export const ORDER_STATUSES: Array<{
  value: ProductionStatus;
  label: string;
  shortLabel: string;
}> = [
  { value: "pending", label: "Pedido recebido", shortLabel: "Recebido" },
  { value: "printed", label: "Etiqueta impressa", shortLabel: "Impresso" },
  { value: "separated", label: "Pedido separado", shortLabel: "Separado" },
  { value: "delivered", label: "Pedido entregue", shortLabel: "Entregue" },
  { value: "cancelled", label: "Pedido cancelado", shortLabel: "Cancelado" },
];

export const KITCHEN_STATUSES = ORDER_STATUSES.filter(
  (status): status is (typeof ORDER_STATUSES)[number] & {
    value: KitchenProductionStatus;
  } => status.value !== "cancelled",
);

export type CartItem = OrderCreateItem & {
  item_name: string;
  unit_price: number;
};

export function addToCart(current: CartItem[], incoming: CartItem): CartItem[] {
  const existingIndex = current.findIndex(
    (item) =>
      item.menu_item_id === incoming.menu_item_id && item.size === incoming.size,
  );
  if (existingIndex < 0) return [...current, incoming];

  return current.map((item, index) =>
    index === existingIndex
      ? {
          ...item,
          quantity: Math.min(10, item.quantity + incoming.quantity),
          notes: incoming.notes || item.notes,
        }
      : item,
  );
}

export function cartQuantity(items: CartItem[]): number {
  return items.reduce((total, item) => total + item.quantity, 0);
}

export function cartTotal(items: CartItem[]): number {
  return items.reduce(
    (total, item) => total + item.quantity * item.unit_price,
    0,
  );
}

export function menuItemById(items: MenuItem[], id: string) {
  return items.find((item) => item.id === id);
}

export function formatMealTime(value: string | null): string {
  if (!value) return "Sem horário";
  if (/^\d{2}:\d{2}/.test(value)) return value.slice(0, 5);
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function nextKitchenStatus(
  current: ProductionStatus,
): KitchenProductionStatus | null {
  if (current === "pending") return "printed";
  if (current === "printed") return "separated";
  if (current === "separated") return "delivered";
  return null;
}
