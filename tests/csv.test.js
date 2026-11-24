import { describe, expect, it } from "vitest";
import { getDatasetStats, parseCSV, searchRows, serializeCSV } from "../src/csv.js";

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
