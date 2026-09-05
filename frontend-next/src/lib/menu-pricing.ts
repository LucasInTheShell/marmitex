import type { MenuItem, SizeOption } from "./types";

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function priceForSize(item: MenuItem, size: SizeOption): number | null {
  if (!item.size_options.includes(size)) return null;
  return item.size_prices?.[size] ?? item.price;
}

export function menuPriceLabel(item: MenuItem): string {
  const prices = item.size_options.map((size) => priceForSize(item, size))
    .filter((price): price is number => price !== null);
  if (!prices.length) return "Sem preço";
  const minimum = Math.min(...prices);
  return `${Math.max(...prices) !== minimum ? "A partir de " : ""}${currency.format(minimum)}`;
}
