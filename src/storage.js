const STORAGE_KEY = "fintrack.workspace.v1";
const STORAGE_VERSION = 1;
const PERSISTED_KEYS = ["tx", "budgets", "goals", "holdings", "accounts"];

function browserStorage() {
  try { return globalThis.localStorage; } catch { return null; }
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validCollection(value) {
  return Array.isArray(value) && value.every((item) => Array.isArray(item));
}

export function loadWorkspace(storage = browserStorage()) {
  try {
    const raw = storage?.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!isRecord(parsed) || parsed.version !== STORAGE_VERSION || !isRecord(parsed.data)) return {};
    return Object.fromEntries(
      PERSISTED_KEYS
        .filter((key) => validCollection(parsed.data[key]))
        .map((key) => [key, parsed.data[key]])
    );
  } catch {
    return {};
  }
}

export function saveWorkspace(state, storage = browserStorage()) {
  if (!isRecord(state) || !storage) return false;
  const data = Object.fromEntries(
    PERSISTED_KEYS
      .filter((key) => validCollection(state[key]))
      .map((key) => [key, state[key]])
  );
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify({ version: STORAGE_VERSION, data }));
    return true;
  } catch {
    return false;
  }
}

export function clearWorkspace(storage = browserStorage()) {
  try {
    storage?.removeItem(STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

export const workspaceStorageKey = STORAGE_KEY;
