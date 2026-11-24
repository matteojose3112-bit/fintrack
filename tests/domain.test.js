import { describe, expect, it } from "vitest";
import {
  accountBalances, createAccount, createCategory, createRecurringRule, createTransaction,
  createTransfer, materializeRecurringTransaction, nextOccurrence, summarizeCashFlow,
  validateTransferPair
} from "../src/domain.js";

const ids = (() => { let n = 0; return () => "test" + (++n); })();

describe("financial domain", () => {
  it("validates and creates accounts, categories and transactions", () => {
    const account = createAccount({ name: "Daily", type: "checking", currency: "USD" }, ids);
    const category = createCategory({ name: "Groceries" }, ids);
    const transaction = createTransaction({
      accountId: account.id, categoryId: category.id, description: "Market",
      type: "expense", amountMinor: 1250, currency: "USD", date: "2026-11-24"
    }, ids);
    expect(account.id).toMatch(/^acct_/);
    expect(category.name).toBe("Groceries");
    expect(transaction.amountMinor).toBe(1250);
    expect(() => createTransaction({ ...transaction, amountMinor: -1 }, ids)).toThrow(RangeError);
    expect(() => createAccount({ name: "Bad", type: "unknown" }, ids)).toThrow(RangeError);
  });

  it("creates balanced paired transfer entries", () => {
    const pair = createTransfer({
      fromAccountId: "acct_a", toAccountId: "acct_b", amountMinor: 5000,
      currency: "USD", date: "2026-11-24"
    }, ids);
    expect(pair).toHaveLength(2);
    expect(pair[0].transferId).toBe(pair[1].transferId);
    expect(pair[0].transferSide).toBe("out");
    expect(pair[1].transferSide).toBe("in");
    expect(validateTransferPair(pair)).toBe(true);
    expect(validateTransferPair([pair[0]])).toBe(false);
  });

  it("calculates balances from opening amounts and posted entries", () => {
    const accounts = [{ id: "a", currency: "USD", openingBalanceMinor: 10000 }];
    const transactions = [
      { accountId: "a", currency: "USD", type: "income", amountMinor: 2500 },
      { accountId: "a", currency: "USD", type: "expense", amountMinor: 400 }
    ];
    expect(accountBalances(accounts, transactions)[0].balanceMinor).toBe(12100);
  });

  it("calculates separate account balances from assigned transactions and transfers", () => {
    const accounts = [
      { id: "checking", currency: "USD", openingBalanceMinor: 100000 },
      { id: "savings", currency: "USD", openingBalanceMinor: 50000 }
    ];
    const pair = createTransfer({ fromAccountId: "checking", toAccountId: "savings", amountMinor: 20000, currency: "USD", date: "2026-11-24" }, ids);
    const transactions = [
      { accountId: "checking", currency: "USD", type: "income", amountMinor: 30000 },
      { accountId: "checking", currency: "USD", type: "expense", amountMinor: 10000 }
    ];
    expect(accountBalances(accounts, [...transactions, ...pair])).toEqual([
      { accountId: "checking", currency: "USD", balanceMinor: 100000 },
      { accountId: "savings", currency: "USD", balanceMinor: 70000 }
    ]);
  });

  it("reports cash flow while excluding internal transfers", () => {
    const rows = [
      { type: "income", amountMinor: 10000, currency: "USD", date: "2026-11-01" },
      { type: "expense", amountMinor: 2500, currency: "USD", date: "2026-11-02" },
      { type: "income", amountMinor: 7000, currency: "USD", date: "2026-11-02", transferId: "t1" },
      { type: "expense", amountMinor: 100, currency: "COP", date: "2026-11-02" }
    ];
    const result = summarizeCashFlow(rows, { from: "2026-11-01", to: "2026-11-30", currency: "USD" });
    expect(result).toEqual({ incomeMinor: 10000, expenseMinor: 2500, netMinor: 7500, transactionCount: 2 });
    expect(result.incomeMinor - result.expenseMinor).toBe(7500);
  });

  it("advances daily, weekly, monthly and yearly recurrence safely", () => {
    expect(nextOccurrence("2026-01-31", "monthly")).toBe("2026-02-28");
    expect(nextOccurrence("2024-02-29", "yearly")).toBe("2025-02-28");
    expect(nextOccurrence("2026-11-24", "weekly")).toBe("2026-12-01");
    expect(nextOccurrence("2026-11-24", "biweekly")).toBe("2026-12-08");
  });

  it("materializes a due recurring transaction and advances its rule", () => {
    const rule = createRecurringRule({
      accountId: "acct_a", description: "Rent", type: "expense", amountMinor: 95000,
      currency: "USD", frequency: "monthly", startDate: "2026-11-01"
    }, ids);
    const result = materializeRecurringTransaction(rule, "2026-11-01", ids);
    expect(result.transaction.recurringRuleId).toBe(rule.id);
    expect(result.updatedRule.nextDate).toBe("2026-12-01");
    expect(() => materializeRecurringTransaction(result.updatedRule, "2026-11-01", ids)).toThrow(RangeError);
  });

  it("rejects invalid dates, cross-account transfers and malformed recurrence", () => {
    expect(() => createTransfer({ fromAccountId: "a", toAccountId: "a", amountMinor: 10, date: "2026-11-01" }, ids)).toThrow(RangeError);
    expect(() => createCategory({ name: "Bad", kind: "transfer" }, ids)).toThrow(RangeError);
    expect(() => createRecurringRule({ accountId: "a", description: "Rent", type: "expense", amountMinor: 100, frequency: "hourly", startDate: "2026-11-01" }, ids)).toThrow(RangeError);
    expect(() => createTransaction({ accountId: "a", description: "Bad", type: "expense", amountMinor: 10, date: "not-a-date" }, ids)).toThrow(TypeError);
  });
});
