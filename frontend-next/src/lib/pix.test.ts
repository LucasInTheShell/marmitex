import { describe, expect, it } from "vitest";
import { paymentLabel, pixControls } from "./orders";
import type { PaymentStatus } from "./types";

const cutoff = "2026-09-04T11:30:00-03:00";
const order = { payment_method: "pix", payment_status: "pending", production_status: "pending" } as const;

describe("Asaas Pix controls", () => {
  it("allows payment and delivery switch only before cutoff", () => {
    expect(pixControls(order, cutoff, Date.parse(cutoff) - 1).canPay).toBe(true);
    expect(pixControls(order, cutoff, Date.parse(cutoff)).canPay).toBe(false);
    expect(pixControls(order, cutoff, Date.parse(cutoff)).canSwitch).toBe(false);
    expect(pixControls(order, cutoff, null).canPay).toBe(false);
  });
  it.each<PaymentStatus>(["paid", "processing", "refunded", "review_required", "cancelled"])(
    "never shows a payable code or switch for %s", (payment_status) => {
      const controls = pixControls({ ...order, payment_status }, cutoff, Date.parse(cutoff) - 1);
      expect(controls.canPay).toBe(false);
      expect(controls.canSwitch).toBe(false);
    },
  );
  it("explains financial review without claiming the payment was refunded", () => {
    expect(paymentLabel("pix", "review_required")).toContain("análise");
    expect(paymentLabel("pix", "review_required")).not.toContain("estornado");
  });
});
