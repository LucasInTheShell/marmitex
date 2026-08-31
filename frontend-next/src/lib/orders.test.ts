import { describe, expect, it } from "vitest";

import { addToCart, cartQuantity, cartTotal } from "@/lib/orders";

describe("order cart", () => {
  it("merges equal dish and size without losing a note", () => {
    const first = addToCart([], {
      menu_item_id: "dish-1",
      item_name: "Frango",
      size: "M",
      quantity: 1,
      unit_price: 24.9,
      notes: "Sem cebola",
    });
    const result = addToCart(first, {
      ...first[0],
      quantity: 2,
      notes: "",
    });

    expect(result).toHaveLength(1);
    expect(result[0].quantity).toBe(3);
    expect(result[0].notes).toBe("Sem cebola");
  });

  it("keeps different sizes as separate lines and calculates totals", () => {
    const items = [
      {
        menu_item_id: "dish-1",
        item_name: "Frango",
        size: "M" as const,
        quantity: 2,
        unit_price: 20,
      },
      {
        menu_item_id: "dish-1",
        item_name: "Frango",
        size: "G" as const,
        quantity: 1,
        unit_price: 25,
      },
    ];

    expect(cartQuantity(items)).toBe(3);
    expect(cartTotal(items)).toBe(65);
  });
});
