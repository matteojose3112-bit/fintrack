import { describe, expect, it } from "vitest";
import { createImportAuditEntries } from "../src/audit.js";
describe("import audit trail", () => {
  it("records all row outcomes with a timestamp and source filename", () => {
    const preview = { valid: [{ row: 2, transaction: ["Salary"] }], possibleMatches: [{ row: 3, transaction: ["Market"] }, { row: 4, transaction: ["Cafe"] }], duplicates: [{ row: 5, transaction: ["Rent"] }], invalid: [{ row: 6, values: ["", "Bad row"], errors: ["Invalid date"] }] };
    const entries = createImportAuditEntries(preview, { 3: "import", 4: "skip" }, "bank.csv", "2026-11-24T12:00:00.000Z");
    expect(entries.map(entry => entry[1])).toEqual(["imported", "imported_as_new", "skipped_possible_match", "duplicate_skipped", "invalid_skipped"]);
    expect(entries.every(entry => entry[0] === "2026-11-24T12:00:00.000Z" && entry[2] === "bank.csv")).toBe(true);
    expect(entries[2][5]).toMatch(/left unchanged/i);
  });
  it("rejects incomplete previews", () => { expect(() => createImportAuditEntries({ valid: [] })).toThrow(TypeError); });
});
