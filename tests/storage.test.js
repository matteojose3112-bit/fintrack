import { beforeEach, describe, expect, it } from "vitest";
import { clearWorkspace, loadWorkspace, saveWorkspace, workspaceStorageKey } from "../src/storage.js";

function createStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

describe("workspace storage", () => {
  let storage;
  beforeEach(() => { storage = createStorage(); });

  it("returns an empty workspace when no saved state exists", () => {
    expect(loadWorkspace(storage)).toEqual({});
  });

  it("saves and restores supported workspace collections", () => {
    const state = { tx: [["Pay", "Income", "Today", 100, "income"]], budgets: [["Food", 20, 50, "mint"]], goals: [["Reserve", 10, 100]], holdings: [], accounts: [], page: "Overview" };
    expect(saveWorkspace(state, storage)).toBe(true);
    expect(loadWorkspace(storage)).toEqual({
      tx: state.tx, budgets: state.budgets, goals: state.goals, holdings: [], accounts: []
    });
  });

  it("persists paired transfer ledger entries", () => {
    const pair = [
      { id: "txn_out", transferId: "trf_1", accountId: "Main checking", type: "expense", amountMinor: 12500, currency: "USD", date: "2026-11-24", transferSide: "out" },
      { id: "txn_in", transferId: "trf_1", accountId: "Savings account", type: "income", amountMinor: 12500, currency: "USD", date: "2026-11-24", transferSide: "in" }
    ];
    expect(saveWorkspace({ transfers: [pair] }, storage)).toBe(true);
    expect(loadWorkspace(storage)).toEqual({ transfers: [pair] });
  });

  it("ignores unknown schema versions and malformed JSON", () => {
    storage.setItem(workspaceStorageKey, JSON.stringify({ version: 99, data: { tx: [["bad"]] } }));
    expect(loadWorkspace(storage)).toEqual({});
    storage.setItem(workspaceStorageKey, "{");
    expect(loadWorkspace(storage)).toEqual({});
  });

  it("ignores invalid collections without discarding valid ones", () => {
    storage.setItem(workspaceStorageKey, JSON.stringify({ version: 1, data: { tx: [["ok"]], budgets: "bad" } }));
    expect(loadWorkspace(storage)).toEqual({ tx: [["ok"]] });
  });

  it("clears the saved workspace", () => {
    saveWorkspace({ tx: [], budgets: [], goals: [], holdings: [], accounts: [] }, storage);
    expect(clearWorkspace(storage)).toBe(true);
    expect(loadWorkspace(storage)).toEqual({});
  });

  it("fails safely when browser storage is unavailable", () => {
    const blocked = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }, removeItem() { throw new Error("blocked"); } };
    expect(loadWorkspace(blocked)).toEqual({});
    expect(saveWorkspace({ tx: [] }, blocked)).toBe(false);
    expect(clearWorkspace(blocked)).toBe(false);
  });
});
