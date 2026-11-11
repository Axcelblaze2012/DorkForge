import type {
  ComposerFields,
  Diagnostic,
  QueryPreview,
  SearchResponse,
  ServerInfo,
  ServerPreset,
} from "@/types";

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function root(config: ApiConfig): string {
  return config.baseUrl.trim().replace(/\/+$/, "");
}

async function request<T>(
  config: ApiConfig,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (config.apiKey) headers.set("X-API-Key", config.apiKey);

  const response = await fetch(`${root(config)}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      // Keep the status text when the body is not JSON.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface CreatePresetBody {
  title: string;
  description: string;
  query: string;
  category: string;
}

interface ServerHealth {
  status: string;
  environment?: string;
}

interface ServerVersion {
  name: string;
  version: string;
}

export interface SearchBody {
  query: string;
  mode?: string;
  page?: number;
  per_page?: number;
  language?: string;
  region?: string;
  save_history?: boolean;
}

export const api = {
  health(config: ApiConfig): Promise<ServerHealth> {
    return request<ServerHealth>(config, "/api/v1/health");
  },

  version(config: ApiConfig): Promise<ServerVersion> {
    return request<ServerVersion>(config, "/api/v1/version");
  },

  async listPresets(config: ApiConfig): Promise<ServerPreset[]> {
    const res = await request<{ presets: ServerPreset[]; total: number } | ServerPreset[]>(
      config,
      "/api/v1/presets",
    );
    return Array.isArray(res) ? res : res.presets;
  },

  createPreset(config: ApiConfig, body: CreatePresetBody): Promise<ServerPreset> {
    return request<ServerPreset>(config, "/api/v1/presets", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  deletePreset(config: ApiConfig, id: number): Promise<void> {
    return request<void>(config, `/api/v1/presets/${id}`, { method: "DELETE" });
  },

  setFavorite(
    config: ApiConfig,
    id: number,
    favorite: boolean,
  ): Promise<ServerPreset> {
    return request<ServerPreset>(
      config,
      `/api/v1/presets/${id}/favorite?value=${favorite}`,
      {
        method: "POST",
      },
    );
  },

  previewQuery(
    config: ApiConfig,
    fields: ComposerFields,
  ): Promise<QueryPreview & { compatibility?: unknown }> {
    return request<QueryPreview & { compatibility?: unknown }>(
      config,
      "/api/v1/query/composer/preview",
      {
        method: "POST",
        body: JSON.stringify({
          terms: fields.terms,
          domain: fields.domain,
          filetype: fields.filetype,
          title_term: fields.titleTerm,
          url_term: fields.urlTerm,
          exact_phrase: fields.exactPhrase,
          exclude_terms: fields.excludeTerm,
          time_range: fields.timeRange,
          region: fields.region,
        }),
      },
    );
  },

  explainQuery(
    config: ApiConfig,
    query: string,
  ): Promise<{
    rendered_query: string;
    operators: string[];
    diagnostics: Diagnostic[];
    complexity: Record<string, unknown>;
    compatibility: Record<string, unknown>;
  }> {
    return request(config, "/api/v1/query/explain", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },

  search(config: ApiConfig, body: SearchBody): Promise<SearchResponse> {
    return request<SearchResponse>(config, "/api/v1/search", {
      method: "POST",
      body: JSON.stringify({
        mode: "universal",
        page: 1,
        per_page: 20,
        language: "",
        region: "",
        save_history: true,
        ...body,
      }),
    });
  },

};

/**
 * Checks whether an Atlas server answers. `/health` is the liveness check;
 * name, version, and preset count are filled in best-effort so an older
 * server still registers as online.
 */
export async function probeServer(config: ApiConfig): Promise<ServerInfo | null> {
  try {
    const health = await api.health(config);
    const [version, presets] = await Promise.allSettled([
      api.version(config),
      api.listPresets(config),
    ]);

    return {
      status: health.status || "ok",
      app: version.status === "fulfilled" ? version.value.name : "Dork Atlas",
      version: version.status === "fulfilled" ? version.value.version : "",
      presets: presets.status === "fulfilled" ? presets.value.length : 0,
    };
  } catch {
    try {
      const presets = await api.listPresets(config);
      return {
        status: "ok",
        app: "Dork Atlas",
        version: "",
        presets: presets.length,
      };
    } catch {
      return null;
    }
  }
}
