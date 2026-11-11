export const CATEGORIES = [
  "Site Discovery",
  "Public Documents",
  "Technology",
  "Content Research",
  "Security & Policy",
  "Learning",
] as const;

export type Category = (typeof CATEGORIES)[number];

export type PresetScope = "Scoped" | "General";
export type PresetSource = "builtin" | "custom";

export interface Preset {
  id: string;
  serverId?: number;
  legacyId?: string;
  title: string;
  description: string;
  category: Category;
  query: string;
  scope: PresetScope;
  source: PresetSource;
  tags?: string[];
}

export interface RecentSearch {
  id: string;
  query: string;
  label: string;
  at: number;
  mode: "google" | "atlas";
  resultCount?: number;
}

export type View = "all" | "favorites" | "custom" | "recent";

export interface ComposerFields {
  terms: string;
  domain: string;
  filetype: string;
  titleTerm: string;
  urlTerm: string;
  exactPhrase: string;
  excludeTerm: string;
  timeRange: string;
  region: string;
}

export interface Diagnostic {
  level: "info" | "warning" | "error";
  code: string;
  message: string;
}

export interface QueryPreview {
  query: string;
  operators: string[];
  diagnostics: Diagnostic[];
}

export interface ResultCard {
  title: string;
  url: string;
  domain: string;
  snippet: string;
  provider: string;
  provider_kind: string;
  found_by: string[];
  engine: string | null;
  published_date: string | null;
  score: number;
}

export interface ProviderStatus {
  provider: string;
  kind: string;
  status: string;
  latency_ms: number;
  count: number;
  error: string | null;
  total_estimated: number | null;
}

export interface SearchResponse {
  query: string;
  rendered_query: string;
  mode: string;
  results: ResultCard[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  providers_used: string[];
  provider_statuses: ProviderStatus[];
  warnings: string[];
  diagnostics: Diagnostic[];
  operators: string[];
  dedup_removed: number;
  filters_applied_locally: boolean;
  elapsed_ms: number;
  cached: boolean;
  history_id: number | null;
}

export interface ServerPreset {
  id: number;
  slug: string;
  title: string;
  description: string;
  query: string;
  category: string;
  scope: string;
  builtin: boolean;
  favorite: boolean;
  use_count: number;
  last_used_at: string | null;
}

export interface ServerInfo {
  status: string;
  app: string;
  version: string;
  presets: number;
}

export interface ServerState {
  status: "unknown" | "checking" | "online" | "offline";
  info: ServerInfo | null;
}
