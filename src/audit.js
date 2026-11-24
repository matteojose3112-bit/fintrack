export function createImportAuditEntries(preview, decisions = {}, fileName = "CSV import", timestamp = new Date().toISOString()) {
  if (!preview || !Array.isArray(preview.valid) || !Array.isArray(preview.possibleMatches) || !Array.isArray(preview.duplicates) || !Array.isArray(preview.invalid)) throw new TypeError("A complete import preview is required.");
  const entries = [];
  const add = (row, action, description, detail) => entries.push([timestamp, action, fileName, row, description || "", detail || ""]);
  for (const item of preview.valid) add(item.row, "imported", item.transaction?.[0], "New transaction added");
  for (const item of preview.possibleMatches) {
    const imported = decisions[item.row] === "import";
    add(item.row, imported ? "imported_as_new" : "skipped_possible_match", item.transaction?.[0], imported ? "Possible match reviewed; separate record added" : "Possible match left unchanged");
  }
  for (const item of preview.duplicates) add(item.row, "duplicate_skipped", item.transaction?.[0], "Exact duplicate excluded");
  for (const item of preview.invalid) add(item.row, "invalid_skipped", item.values?.[1] || "", item.message || (item.errors || []).join(" "));
  return entries.sort((a, b) => Number(a[3]) - Number(b[3]));
}
