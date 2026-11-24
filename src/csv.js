/**
 * Parse CSV text into an array of records.
 * Supports quoted fields, escaped quotes, commas, and newlines inside quotes.
 * The first row is treated as the header row.
 */
export function parseCSV(text) {
  if (typeof text !== "string") {
    throw new TypeError("CSV input must be a string.");
  }

  const source = text.replace(/^\uFEFF/, "");
  if (source.trim() === "") return { headers: [], rows: [] };

  const records = [];
  let record = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (char === '"') {
      if (quoted && next === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      record.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      record.push(field);
      records.push(record);
      record = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (quoted) throw new Error("The CSV contains an unclosed quoted field.");

  record.push(field);
  records.push(record);

  while (records.length && records.at(-1).every((value) => value === "")) {
    records.pop();
  }

  if (!records.length) return { headers: [], rows: [] };

  const headers = records.shift().map((header, index) => {
    const cleaned = header.trim();
    return cleaned || `Column ${index + 1}`;
  });

  const rows = records.map((values) =>
    headers.map((_, index) => values[index] ?? "")
  );

  return { headers, rows };
}

export function getDatasetStats(rows, columnCount) {
  const emptyCells = rows.reduce(
    (total, row) => total + row.filter((value) => value.trim() === "").length,
    0
  );

  return {
    rowCount: rows.length,
    columnCount,
    emptyCells,
  };
}

export function searchRows(rows, query) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return rows;

  return rows.filter((row) =>
    row.some((value) => value.toLocaleLowerCase().includes(normalizedQuery))
  );
}


/**
 * Serialize tabular data as CSV and neutralize formula-like text cells.
 */
export function serializeCSV(headers, rows) {
  if (!Array.isArray(headers) || !Array.isArray(rows)) {
    throw new TypeError("CSV headers and rows must be arrays.");
  }
  const encodeCell = (value) => {
    let text = value == null ? "" : String(value);
    if (typeof value === "string" && /^\s*[=+@-]/.test(text)) text = "'" + text;
    if (/[",\r\n]/.test(text)) text = '"' + text.replace(/"/g, '""') + '"';
    return text;
  };
  return [headers, ...rows].map((row) => {
    if (!Array.isArray(row)) throw new TypeError("Each CSV row must be an array.");
    return row.map(encodeCell).join(",");
  }).join("\r\n") + "\r\n";
}
