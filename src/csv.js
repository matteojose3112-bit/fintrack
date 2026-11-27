/**
 * Parse CSV text into records using a strict RFC 4180-style state machine.
 * Quoted fields may contain commas, escaped quotes, and line breaks.
 * The first record is treated as the header row.
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
  let inQuotes = false;
  let quoteClosed = false;

  const finishField = () => {
    record.push(field);
    field = "";
    quoteClosed = false;
  };

  const finishRecord = () => {
    finishField();
    records.push(record);
    record = [];
  };

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (inQuotes) {
      if (char === '"') {
        if (next === '"') {
          field += '"';
          index += 1;
        } else {
          inQuotes = false;
          quoteClosed = true;
        }
      } else {
        field += char;
      }
      continue;
    }

    if (quoteClosed) {
      if (char === ",") {
        finishField();
      } else if (char === "\n" || char === "\r") {
        if (char === "\r" && next === "\n") index += 1;
        finishRecord();
      } else {
        throw new Error("Unexpected character after a closing CSV quote.");
      }
      continue;
    }

    if (char === '"') {
      if (field.length > 0) {
        throw new Error("A quote may only begin at the start of a CSV field.");
      }
      inQuotes = true;
    } else if (char === ",") {
      finishField();
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && next === "\n") index += 1;
      finishRecord();
    } else {
      field += char;
    }
  }

  if (inQuotes) {
    throw new Error("The CSV contains an unclosed quoted field.");
  }

  finishRecord();

  while (records.length && records.at(-1).every((value) => value === "")) {
    records.pop();
  }

  if (!records.length) return { headers: [], rows: [] };

  const headers = records.shift().map((header, index) => {
    const cleaned = header.trim();
    return cleaned || `Column ${index + 1}`;
  });

  const rows = records.map((values, index) => {
    if (values.length > headers.length) {
      throw new Error(
        `CSV row ${index + 2} contains more fields than the header row.`,
      );
    }
    return headers.map((_, columnIndex) => values[columnIndex] ?? "");
  });

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
