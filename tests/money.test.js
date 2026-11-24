import { describe, expect, it } from "vitest";
import { addMoney, formatMoney, parseMoney, subtractMoney, supportedCurrencies } from "../src/money.js";

describe("money utilities", () => {
  it("parses decimal currency amounts into integer minor units", () => {
    expect(parseMoney("12.34", "USD")).toBe(1234);
    expect(parseMoney("-0.50", "USD")).toBe(-50);
    expect(parseMoney("125000", "COP")).toBe(125000);
  });

  it("rejects invalid and over-precise input", () => {
    expect(() => parseMoney("12.345", "USD")).toThrow(RangeError);
    expect(() => parseMoney("12.5", "COP")).toThrow(RangeError);
    expect(() => parseMoney("12,50", "USD")).toThrow(TypeError);
    expect(() => parseMoney("1", "XYZ")).toThrow(RangeError);
  });

  it("formats integer minor units using the selected currency", () => {
    expect(formatMoney(1234, "USD", "en-US")).toBe("$12.34");
    expect(formatMoney(125000, "COP", "en-US")).toContain("125,000");
  });

  it("adds and subtracts without floating-point drift", () => {
    expect(addMoney(10, 20)).toBe(30);
    expect(subtractMoney(100, 35)).toBe(65);
    expect(() => addMoney(Number.MAX_SAFE_INTEGER, 1)).toThrow(RangeError);
  });

  it("exposes the supported currency list", () => {
    expect(supportedCurrencies()).toEqual(["USD", "COP", "CAD", "EUR", "GBP"]);
  });
});
