import { describe, expect, it } from "vitest";
import { menuPriceLabel, priceForSize } from "./menu-pricing";
import { addToCart, cartTotal } from "./orders";
import type { MenuItem } from "./types";

const dish: MenuItem = {
  id: "dish", name: "Frango", description: null, size_options: ["P", "M", "G"],
  price: 18, image_url: null, images: [], size_prices: { P: 12.99, G: 23.9 },
};

describe("size pricing", () => {
  it("uses the chosen size and falls back to a legacy single price", () => {
    expect(priceForSize(dish, "P")).toBe(12.99);
    expect(priceForSize(dish, "M")).toBe(18);
    expect(priceForSize({ ...dish, size_prices: undefined }, "G")).toBe(18);
    expect(priceForSize({ ...dish, size_options: ["P"] }, "G")).toBeNull();
    expect(priceForSize({ ...dish, size_prices: { P: 0 } }, "P")).toBe(0);
  });
  it("distinguishes no price, a single price and a range", () => {
    expect(menuPriceLabel(dish)).toContain("A partir de");
    expect(menuPriceLabel({ ...dish, size_prices: {} })).not.toContain("A partir de");
    expect(menuPriceLabel({ ...dish, price: null, size_prices: {} })).toBe("Sem preço");
  });
  it("keeps sizes separate in the cart and charges their respective prices", () => {
    let cart = addToCart([], { menu_item_id: dish.id, item_name: dish.name, size: "P",
      quantity: 2, unit_price: priceForSize(dish, "P")! });
    cart = addToCart(cart, { menu_item_id: dish.id, item_name: dish.name, size: "G",
      quantity: 1, unit_price: priceForSize(dish, "G")! });
    expect(cart).toHaveLength(2);
    expect(cartTotal(cart)).toBeCloseTo(49.88, 2);
  });
});
