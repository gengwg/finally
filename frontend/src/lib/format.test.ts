import { describe, expect, it } from "vitest";
import {
  formatMoney,
  formatPercent,
  formatPrice,
  formatQuantity,
  formatSignedMoney,
  toneClass,
} from "./format";

describe("money formatting", () => {
  it("formats positive and zero amounts with two decimals", () => {
    expect(formatMoney(10000)).toBe("$10,000.00");
    expect(formatMoney(0)).toBe("$0.00");
    expect(formatMoney(8079.5)).toBe("$8,079.50");
  });

  it("renders a dash for missing values", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatPrice(undefined)).toBe("—");
    expect(formatPercent(null)).toBe("—");
  });

  it("puts the sign outside the currency symbol for P&L", () => {
    expect(formatSignedMoney(15)).toBe("+$15.00");
    expect(formatSignedMoney(-40)).toBe("-$40.00");
    expect(formatSignedMoney(0)).toBe("$0.00");
  });
});

describe("percent formatting", () => {
  it("signs both directions and keeps two decimals", () => {
    expect(formatPercent(0.784)).toBe("+0.78%");
    expect(formatPercent(-4)).toBe("-4.00%");
    expect(formatPercent(0)).toBe("0.00%");
  });
});

describe("quantities", () => {
  it("keeps whole shares whole and fractional shares precise", () => {
    expect(formatQuantity(10)).toBe("10");
    expect(formatQuantity(0.5)).toBe("0.5000");
  });
});

describe("toneClass", () => {
  it("maps sign to colour, treating zero as neutral", () => {
    expect(toneClass(1)).toBe("text-up");
    expect(toneClass(-1)).toBe("text-down");
    expect(toneClass(0)).toBe("text-ink-muted");
    expect(toneClass(null)).toBe("text-ink-muted");
  });
});
