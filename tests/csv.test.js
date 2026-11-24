import { describe, expect, it } from "vitest";
import { getDatasetStats, parseCSV, searchRows, serializeCSV } from "../src/csv.js";
import { previewTransactionImport, suggestColumnMapping } from "../src/import.js";

describe("parseCSV", () => {
  it("parses headers and rows", () => {
    expect(parseCSV("name,city\nAda,London")).toEqual({
      headers: ["name", "city"],
      rows: [["Ada", "London"]],
    });
  });

  it("supports commas and newlines inside quoted fields", () => {
    expect(parseCSV('name,note\nAda,"London, UK"\nGrace,"First line\nSecond line"').rows).toEqual([
      ["Ada", "London, UK"],
      ["Grace", "First line\nSecond line"],
    ]);
  });

  it("supports escaped quote characters", () => {
    expect(parseCSV('name,quote\nAda,"She said ""hello"""').rows).toEqual([
      ["Ada", 'She said "hello"'],
    ]);
  });

  it("fills missing trailing values and names blank columns", () => {
    expect(parseCSV("name,\nAda").rows).toEqual([["Ada", ""]]);
    expect(parseCSV("name,\nAda").headers).toEqual(["name", "Column 2"]);
  });

  it("handles a byte order mark and empty input", () => {
    expect(parseCSV("\uFEFFname\nAda").headers).toEqual(["name"]);
    expect(parseCSV("")).toEqual({ headers: [], rows: [] });
  });

  it("rejects unclosed quoted fields", () => {
    expect(() => parseCSV('name,note\nAda,"unfinished')).toThrow(/unclosed/i);
  });
});

describe("dataset helpers", () => {
  it("counts empty cells", () => {
    expect(getDatasetStats([["Ada", ""], ["", "Paris"]], 2)).toEqual({
      rowCount: 2,
      columnCount: 2,
      emptyCells: 2,
    });
  });

  it("searches every cell without case sensitivity", () => {
    expect(searchRows([["Ada", "London"], ["Grace", "New York"]], "LON")).toEqual([
      ["Ada", "London"],
    ]);
  });

  it("returns all rows for an empty search", () => {
    const rows = [["Ada"], ["Grace"]];
    expect(searchRows(rows, "  ")).toBe(rows);
  });
});


describe("serializeCSV", () => {
  it("escapes commas, quotes and embedded line breaks", () => {
    expect(serializeCSV(["name", "note"], [["Ada", 'Said "hello", twice'], ["Grace", "line 1\nline 2"]])).toBe(
      'name,note\r\nAda,"Said ""hello"", twice"\r\nGrace,"line 1\nline 2"\r\n'
    );
  });
  it("neutralizes formula-like text while preserving numeric negatives", () => {
    expect(serializeCSV(["description", "amount"], [["=HYPERLINK(1)", -1250], ["  @SUM(A1)", 20]])).toBe(
      "description,amount\r\n'=HYPERLINK(1),-1250\r\n'  @SUM(A1),20\r\n"
    );
  });
  it("handles empty data and rejects invalid input", () => {
    expect(serializeCSV(["name"], [])).toBe("name\r\n");
    expect(() => serializeCSV("name", [])).toThrow(TypeError);
    expect(() => serializeCSV(["name"], [null])).toThrow(TypeError);
  });
});


describe("transaction CSV import", () => {
 const headers=["Date","Description","Category","Type","Amount","Currency"];
 const rows=[["2026-11-20","Groceries","Food","expense","125.50","USD"],["2026-11-21","Salary","Income","income","2400","USD"],["not-a-date","Bad date","Other","expense","10","USD"]];
 it("suggests columns by common header names",()=>expect(suggestColumnMapping(headers)).toEqual({description:"1",category:"2",date:"0",type:"3",amount:"4",currency:"5"}));
 it("validates rows and separates duplicate transactions",()=>{const result=previewTransactionImport(headers,rows,suggestColumnMapping(headers),[["Groceries","Food","2026-11-20",125.5,"expense","USD"]]);expect(result.valid).toHaveLength(1);expect(result.valid[0].transaction).toEqual(["Salary","Income","2026-11-21",2400,"income","USD"]);expect(result.duplicates).toHaveLength(1);expect(result.invalid).toHaveLength(1);expect(result.invalid[0].errors.join(" ")).toMatch(/real date/i)});
 it("requires mandatory columns to be mapped",()=>{const result=previewTransactionImport(headers,rows,{description:"1"});expect(result.valid).toHaveLength(0);expect(result.invalid[0].row).toBe(0);expect(result.invalid[0].message).toMatch(/map a csv column/i)});
 it("rejects unsupported currency and non-positive amounts",()=>{const result=previewTransactionImport(headers,[["2026-11-20","Test","Food","expense","-2","XYZ"]],suggestColumnMapping(headers));expect(result.invalid[0].errors).toHaveLength(2)});
});
