import type { ComposerFields, PresetScope } from "@/types";

export const DEFAULT_REGION = "IN";

export const REGION_OPTIONS = [
  ["IN", "India"],
  ["US", "United States"],
  ["GB", "United Kingdom"],
  ["CA", "Canada"],
  ["AU", "Australia"],
  ["DE", "Germany"],
  ["FR", "France"],
  ["JP", "Japan"],
  ["SG", "Singapore"],
  ["ZZ", "Any region"],
] as const;

export const TIME_RANGE_OPTIONS = [
  ["", "Any time"],
  ["d", "Past 24 hours"],
  ["w", "Past week"],
  ["m", "Past month"],
  ["y", "Past year"],
] as const;

export function regionLabel(code: string): string {
  return REGION_OPTIONS.find(([value]) => value === code)?.[1] ?? code;
}

export function timeRangeLabel(code: string): string {
  return TIME_RANGE_OPTIONS.find(([value]) => value === code)?.[1] ?? "Any time";
}

export const EMPTY_COMPOSER: ComposerFields = {
  terms: "",
  domain: "",
  filetype: "",
  titleTerm: "",
  urlTerm: "",
  exactPhrase: "",
  excludeTerm: "",
  timeRange: "",
  region: DEFAULT_REGION,
};

export function cleanDomain(value: string): string {
  return value
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .split("/")[0]
    .replace(/\s+/g, "");
}

export function resolveTemplate(
  query: string,
  domain: string,
  topic: string,
): string {
  return query
    .replaceAll("{domain}", cleanDomain(domain) || "example.com")
    .replaceAll("{topic}", topic.trim() || "research topic");
}

function relativeDate(rangeCode: string): string {
  const days = { d: 1, w: 7, m: 30, y: 365 }[rangeCode] ?? 0;
  const date = new Date();
  date.setDate(date.getDate() - days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function operator(name: string, value: string): string {
  if (value.includes(" ") || value.includes('"')) {
    return `${name}:"${value.replaceAll('"', "")}"`;
  }
  return `${name}:${value}`;
}

/**
 * Mirrors the backend's canonical composer builder
 * (`app/search/parser/builder.py`) so the local preview and the API agree.
 */
export function buildQuery(fields: ComposerFields): string {
  const parts: string[] = [];

  const terms = fields.terms.trim();
  if (terms) parts.push(terms);

  const domain = cleanDomain(fields.domain);
  if (domain) parts.push(operator("site", domain));

  const filetype = fields.filetype.trim().replace(/^\./, "").toLowerCase();
  if (filetype) parts.push(operator("filetype", filetype));

  const title = fields.titleTerm.trim();
  if (title) parts.push(operator("intitle", title.replaceAll('"', "")));

  const url = fields.urlTerm.trim();
  if (url) parts.push(operator("inurl", url.replaceAll('"', "")));

  const exact = fields.exactPhrase.trim();
  if (exact) parts.push(`"${exact.replaceAll('"', "")}"`);

  const exclusions = fields.excludeTerm
    .trim()
    .split(/[\s,]+/)
    .filter(Boolean);
  for (const term of exclusions) {
    const cleaned = term.replace(/^-/, "").replaceAll('"', "");
    if (cleaned) parts.push(`-${cleaned}`);
  }

  if (["d", "w", "m", "y"].includes(fields.timeRange)) {
    parts.push(`after:${relativeDate(fields.timeRange)}`);
  }

  return parts.join(" ");
}

export function localOperators(fields: ComposerFields): string[] {
  const operators: string[] = [];
  if (cleanDomain(fields.domain)) operators.push("site");
  if (fields.filetype.trim()) operators.push("filetype");
  if (fields.titleTerm.trim()) operators.push("intitle");
  if (fields.urlTerm.trim()) operators.push("inurl");
  if (["d", "w", "m", "y"].includes(fields.timeRange)) operators.push("after");
  return operators.sort();
}

export function googleSearchUrl(query: string, region: string): string {
  const params = new URLSearchParams({ q: query, hl: "en" });
  if (region && region !== "ZZ") params.set("gl", region);
  return `https://www.google.com/search?${params.toString()}`;
}

export function presetScope(query: string): PresetScope {
  return query.includes("{domain}") ? "Scoped" : "General";
}

export type QueryTokenKind =
  | "text"
  | "operator"
  | "phrase"
  | "boolean"
  | "exclude";

export interface QueryToken {
  text: string;
  kind: QueryTokenKind;
}

const TOKEN_RE =
  /("(?:[^"\\]|\\.)*")|((?:site|filetype|intitle|inurl|intext|before|after|related|source|link):(?:"(?:[^"\\]|\\.)*"|[^\s()]+))|(\bAROUND\(\d+\))|(\bOR\b)|((?<!\S)-(?:"(?:[^"\\]|\\.)*"|[^\s]+))/gi;

/**
 * Splits a query into plain text and operator tokens so the preview can
 * show what the search engine will actually read.
 */
export function tokenizeQuery(query: string): QueryToken[] {
  const tokens: QueryToken[] = [];
  let lastIndex = 0;

  for (const match of query.matchAll(TOKEN_RE)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      tokens.push({ text: query.slice(lastIndex, index), kind: "text" });
    }

    const kind: QueryTokenKind = match[1]
      ? "phrase"
      : match[2] || match[3]
        ? "operator"
        : match[4]
          ? "boolean"
          : "exclude";

    tokens.push({ text: match[0], kind });
    lastIndex = index + match[0].length;
  }

  if (lastIndex < query.length) {
    tokens.push({ text: query.slice(lastIndex), kind: "text" });
  }

  return tokens;
}
