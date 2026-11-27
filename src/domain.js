import { addMoney, subtractMoney } from "./money.js";

const ACCOUNT_TYPES = new Set(["checking", "savings", "cash", "credit", "investment", "other"]);
const TRANSACTION_TYPES = new Set(["income", "expense"]);
const CATEGORY_KINDS = new Set(["income", "expense", "both"]);
const FREQUENCIES = new Set(["daily", "weekly", "biweekly", "monthly", "yearly"]);
const CURRENCIES = new Set(["USD", "COP", "CAD", "EUR", "GBP"]);

function requireText(value, field) {
  if (typeof value !== "string" || !value.trim()) throw new TypeError(field + " is required.");
  return value.trim();
}
function requirePositiveInteger(value, field) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new RangeError(field + " must be a positive integer in minor units.");
  return value;
}
function requireDate(value, field = "date") {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new TypeError(field + " must use YYYY-MM-DD.");
  const parsed = new Date(value + "T00:00:00Z");
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new TypeError(field + " must be a real calendar date.");
  return value;
}
function requireCurrency(value) {
  if (!CURRENCIES.has(value)) throw new RangeError("Unsupported currency: " + value);
  return value;
}
function makeId(prefix, idFactory) {
  const id = idFactory();
  if (typeof id !== "string" || !id.trim()) throw new TypeError("The ID factory must return a non-empty string.");
  return prefix + "_" + id.trim();
}

export function createAccount(input, idFactory = () => crypto.randomUUID()) {
  const name = requireText(input?.name, "Account name");
  const type = input?.type ?? "checking";
  if (!ACCOUNT_TYPES.has(type)) throw new RangeError("Unsupported account type: " + type);
  const currency = requireCurrency(input?.currency ?? "USD");
  const openingBalanceMinor = input?.openingBalanceMinor ?? 0;
  if (!Number.isSafeInteger(openingBalanceMinor)) throw new TypeError("Opening balance must be integer minor units.");
  return { id: makeId("acct", idFactory), name, type, currency, openingBalanceMinor, archived: false, createdAt: new Date().toISOString() };
}

export function createCategory(input, idFactory = () => crypto.randomUUID()) {
  const kind = input?.kind ?? "expense";
  if (!CATEGORY_KINDS.has(kind)) throw new RangeError("Category kind must be income, expense or both.");
  return {
    id: makeId("cat", idFactory),
    name: requireText(input?.name, "Category name"),
    kind,
    color: input?.color ?? "neutral",
    archived: false
  };
}

export function createTransaction(input, idFactory = () => crypto.randomUUID()) {
  const type = input?.type;
  if (!TRANSACTION_TYPES.has(type)) throw new RangeError("Transaction type must be income or expense.");
  const currency = requireCurrency(input?.currency ?? "USD");
  const amountMinor = requirePositiveInteger(input?.amountMinor, "Amount");
  return {
    id: makeId("txn", idFactory),
    accountId: requireText(input?.accountId, "Account ID"),
    categoryId: input?.categoryId ? requireText(input.categoryId, "Category ID") : null,
    description: requireText(input?.description, "Description"),
    type,
    amountMinor,
    currency,
    date: requireDate(input?.date),
    notes: typeof input?.notes === "string" ? input.notes.trim() : "",
    recurringRuleId: input?.recurringRuleId ?? null,
    transferId: null,
    createdAt: new Date().toISOString()
  };
}

export function createTransfer(input, idFactory = () => crypto.randomUUID()) {
  const fromAccountId = requireText(input?.fromAccountId, "Source account ID");
  const toAccountId = requireText(input?.toAccountId, "Destination account ID");
  if (fromAccountId === toAccountId) throw new RangeError("A transfer must use two different accounts.");
  const currency = requireCurrency(input?.currency ?? "USD");
  const amountMinor = requirePositiveInteger(input?.amountMinor, "Transfer amount");
  const date = requireDate(input?.date);
  const transferId = makeId("trf", idFactory);
  const common = { transferId, amountMinor, currency, date, categoryId: null, recurringRuleId: null, createdAt: new Date().toISOString() };
  return [
    { ...common, id: makeId("txn", idFactory), accountId: fromAccountId, description: input.description || "Transfer out", type: "expense", transferSide: "out", notes: "" },
    { ...common, id: makeId("txn", idFactory), accountId: toAccountId, description: input.description || "Transfer in", type: "income", transferSide: "in", notes: "" }
  ];
}

export function createRecurringRule(input, idFactory = () => crypto.randomUUID()) {
  const type = input?.type;
  if (!TRANSACTION_TYPES.has(type)) throw new RangeError("Recurring transaction type must be income or expense.");
  const frequency = input?.frequency;
  if (!FREQUENCIES.has(frequency)) throw new RangeError("Unsupported recurrence frequency: " + frequency);
  const startDate = requireDate(input?.startDate, "startDate");
  const endDate = input?.endDate ? requireDate(input.endDate, "endDate") : null;
  if (endDate && endDate < startDate) throw new RangeError("endDate cannot be before startDate.");
  return {
    id: makeId("rrule", idFactory),
    accountId: requireText(input?.accountId, "Account ID"),
    categoryId: input?.categoryId ? requireText(input.categoryId, "Category ID") : null,
    description: requireText(input?.description, "Description"),
    type,
    amountMinor: requirePositiveInteger(input?.amountMinor, "Amount"),
    currency: requireCurrency(input?.currency ?? "USD"),
    frequency,
    startDate,
    nextDate: startDate,
    endDate,
    active: true
  };
}

function addMonthsClamped(dateString, months) {
  const [year, month, day] = dateString.split("-").map(Number);
  const targetMonth = month - 1 + months;
  const targetYear = year + Math.floor(targetMonth / 12);
  const normalizedMonth = ((targetMonth % 12) + 12) % 12;
  const lastDay = new Date(Date.UTC(targetYear, normalizedMonth + 1, 0)).getUTCDate();
  return new Date(Date.UTC(targetYear, normalizedMonth, Math.min(day, lastDay))).toISOString().slice(0, 10);
}
export function nextOccurrence(date, frequency) {
  requireDate(date);
  if (!FREQUENCIES.has(frequency)) throw new RangeError("Unsupported recurrence frequency: " + frequency);
  const day = frequency === "daily" ? 1 : frequency === "weekly" ? 7 : frequency === "biweekly" ? 14 : 0;
  if (day) {
    const result = new Date(date + "T00:00:00Z");
    result.setUTCDate(result.getUTCDate() + day);
    return result.toISOString().slice(0, 10);
  }
  return addMonthsClamped(date, frequency === "monthly" ? 1 : 12);
}

export function materializeRecurringTransaction(rule, occurrenceDate, idFactory = () => crypto.randomUUID()) {
  if (!rule || !rule.active) throw new RangeError("Recurring rule is not active.");
  const date = requireDate(occurrenceDate);
  if (date !== rule.nextDate || date < rule.startDate || (rule.endDate && date > rule.endDate)) {
    throw new RangeError("Occurrence date is outside the due window.");
  }
  const transaction = createTransaction({
    accountId: rule.accountId, categoryId: rule.categoryId, description: rule.description,
    type: rule.type, amountMinor: rule.amountMinor, currency: rule.currency, date,
    recurringRuleId: rule.id
  }, idFactory);
  const nextDate = nextOccurrence(date, rule.frequency);
  return { transaction, updatedRule: { ...rule, nextDate, active: !rule.endDate || nextDate <= rule.endDate } };
}

export function summarizeCashFlow(transactions, { from, to, currency } = {}) {
  const filtered = transactions.filter((tx) =>
    (!from || tx.date >= from) && (!to || tx.date <= to) &&
    (!currency || tx.currency === currency) && !tx.transferId
  );
  const summary = filtered.reduce((summary, tx) => {
    if (tx.type === "income") summary.incomeMinor = addMoney(summary.incomeMinor, tx.amountMinor);
    else if (tx.type === "expense") summary.expenseMinor = addMoney(summary.expenseMinor, tx.amountMinor);
    return summary;
  }, { incomeMinor: 0, expenseMinor: 0, transactionCount: filtered.length });
  summary.netMinor = subtractMoney(summary.incomeMinor, summary.expenseMinor);
  return summary;
}

export function accountBalances(accounts, transactions) {
  return accounts.map((account) => {
    const balanceMinor = transactions.reduce((balance, tx) => {
      if (tx.accountId !== account.id || tx.currency !== account.currency) return balance;
      const signed = tx.type === "income" ? tx.amountMinor : -tx.amountMinor;
      return addMoney(balance, signed);
    }, account.openingBalanceMinor);
    return { accountId: account.id, currency: account.currency, balanceMinor };
  });
}

export function validateTransferPair(transactions) {
  const transfers = new Map();
  for (const tx of transactions.filter((item) => item.transferId)) {
    const group = transfers.get(tx.transferId) ?? [];
    group.push(tx);
    transfers.set(tx.transferId, group);
  }
  return [...transfers.values()].every((pair) =>
    pair.length === 2 &&
    pair.some((tx) => tx.transferSide === "out" && tx.type === "expense") &&
    pair.some((tx) => tx.transferSide === "in" && tx.type === "income") &&
    pair[0].accountId !== pair[1].accountId &&
    Number.isSafeInteger(pair[0].amountMinor) &&
    pair[0].amountMinor > 0 &&
    Number.isSafeInteger(pair[1].amountMinor) &&
    pair[1].amountMinor > 0 &&
    pair[0].accountId !== pair[1].accountId &&
    Number.isSafeInteger(pair[0].amountMinor) &&
    pair[0].amountMinor > 0 &&
    Number.isSafeInteger(pair[1].amountMinor) &&
    pair[1].amountMinor > 0 &&
    pair[0].amountMinor === pair[1].amountMinor &&
    pair[0].currency === pair[1].currency &&
    pair[0].date === pair[1].date
  );
}
