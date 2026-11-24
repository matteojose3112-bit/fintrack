const CURRENCY_SCALE = Object.freeze({ USD: 2, COP: 0, CAD: 2, EUR: 2, GBP: 2 });

function scaleFor(currency) {
  const scale = CURRENCY_SCALE[currency];
  if (scale === undefined) throw new RangeError(`Unsupported currency: ${currency}`);
  return scale;
}

/** Parse a decimal amount into integer minor units without floating-point math. */
export function parseMoney(value, currency = "USD") {
  const scale = scaleFor(currency);
  const input = String(value).trim();
  const match = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(input);
  if (!match) throw new TypeError("Enter a valid decimal amount.");
  const fraction = match[3] ?? "";
  if (fraction.length > scale) {
    throw new RangeError(`${currency} supports at most ${scale} decimal places.`);
  }
  const factor = 10 ** scale;
  const whole = Number(match[2]);
  const fractional = Number((fraction + "0".repeat(scale)).slice(0, scale) || "0");
  const amount = whole * factor + fractional;
  if (!Number.isSafeInteger(amount)) throw new RangeError("Amount exceeds the supported precision.");
  return match[1] === "-" ? -amount : amount;
}

export function formatMoney(minorUnits, currency = "USD", locale = "en-US") {
  scaleFor(currency);
  if (!Number.isSafeInteger(minorUnits)) throw new TypeError("Money must be an integer number of minor units.");
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: CURRENCY_SCALE[currency],
    maximumFractionDigits: CURRENCY_SCALE[currency],
  }).format(minorUnits / (10 ** CURRENCY_SCALE[currency]));
}

export function addMoney(left, right) {
  if (!Number.isSafeInteger(left) || !Number.isSafeInteger(right)) {
    throw new TypeError("Money arithmetic requires integer minor units.");
  }
  const result = left + right;
  if (!Number.isSafeInteger(result)) throw new RangeError("Money total exceeds the supported precision.");
  return result;
}

export function subtractMoney(left, right) {
  if (!Number.isSafeInteger(left) || !Number.isSafeInteger(right)) {
    throw new TypeError("Money arithmetic requires integer minor units.");
  }
  const result = left - right;
  if (!Number.isSafeInteger(result)) throw new RangeError("Money total exceeds the supported precision.");
  return result;
}

export function supportedCurrencies() {
  return Object.keys(CURRENCY_SCALE);
}
