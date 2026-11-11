import { create } from "zustand";
import { persist } from "zustand/middleware";

import { BUILTIN_PRESETS } from "@/data/builtins";
import { presetScope } from "@/lib/query";
import { EMPTY_COMPOSER } from "@/lib/query";
import type {
  Category,
  ComposerFields,
  Preset,
  RecentSearch,
  ServerPreset,
  ServerState,
  View,
} from "@/types";
import { CATEGORIES } from "@/types";

const LEGACY_KEYS = {
  favorites: "dork-atlas-favorites-v1",
  custom: "dork-atlas-custom-v1",
  recent: "dork-atlas-recent-v1",
} as const;

const MIGRATION_FLAG = "dork-atlas-workspace-migrated-v1";

type Persisted = Pick<
  WorkspaceState,
  "favorites" | "custom" | "recent" | "serverIds" | "apiBase" | "apiKey"
>;

interface WorkspaceState {
  favorites: string[];
  custom: Preset[];
  recent: RecentSearch[];
  serverIds: Record<string, number>;
  apiBase: string;
  apiKey: string;
  composer: ComposerFields;
  view: View;
  category: string;
  searchTerm: string;
  server: ServerState;
  setField: (key: keyof ComposerFields, value: string) => void;
  resetComposer: () => void;
  loadQuery: (query: string) => void;
  toggleFavorite: (id: string) => void;
  addCustom: (preset: Preset) => void;
  deleteCustom: (id: string) => void;
  attachServerId: (id: string, serverId: number) => void;
  recordRecent: (entry: RecentSearch) => void;
  setView: (view: View) => void;
  setCategory: (category: string) => void;
  setSearchTerm: (term: string) => void;
  setApiConfig: (baseUrl: string, apiKey: string) => void;
  setServer: (server: ServerState) => void;
  mergeServerPresets: (presets: ServerPreset[]) => void;
}

function asCategory(value: unknown): Category {
  return typeof value === "string" &&
    (CATEGORIES as readonly string[]).includes(value)
    ? (value as Category)
    : "Site Discovery";
}

function normalizeLegacyCustom(items: unknown): Preset[] {
  if (!Array.isArray(items)) return [];

  return items.flatMap((item, index) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const title = String(record.title ?? record.name ?? "").trim();
    const query = String(record.query ?? "").trim();
    if (!title || !query) return [];

    return [
      {
        id:
          typeof record.id === "string" && record.id
            ? record.id
            : `c${Date.now()}-${index}`,
        title,
        description: String(
          record.desc ??
            record.description ??
            "Custom search pattern saved in this workspace.",
        ),
        category: asCategory(record.category),
        query,
        scope: record.scope === "Scoped" ? "Scoped" : presetScope(query),
        source: "custom" as const,
      },
    ];
  });
}

function normalizeLegacyRecent(items: unknown): RecentSearch[] {
  if (!Array.isArray(items)) return [];

  return items
    .flatMap((item, index) => {
      if (!item || typeof item !== "object") return [];
      const record = item as Record<string, unknown>;
      const query = String(record.query ?? "").trim();
      if (!query) return [];

      const parsed = Date.parse(String(record.when ?? ""));
      return [
        {
          id: `legacy-${index}`,
          query,
          label: String(record.label ?? "Google search"),
          at: Number.isNaN(parsed) ? Date.now() : parsed,
          mode: "google" as const,
        },
      ];
    })
    .slice(0, 12);
}

function readLegacy(): Partial<Persisted> {
  if (typeof window === "undefined") return {};

  try {
    if (window.localStorage.getItem(MIGRATION_FLAG)) return {};
    window.localStorage.setItem(MIGRATION_FLAG, "1");

    const favoritesRaw = JSON.parse(
      window.localStorage.getItem(LEGACY_KEYS.favorites) ?? "[]",
    ) as unknown;
    const customRaw = JSON.parse(
      window.localStorage.getItem(LEGACY_KEYS.custom) ?? "[]",
    ) as unknown;
    const recentRaw = JSON.parse(
      window.localStorage.getItem(LEGACY_KEYS.recent) ?? "[]",
    ) as unknown;

    const favorites = Array.isArray(favoritesRaw)
      ? favoritesRaw.filter((value): value is string => typeof value === "string")
      : [];
    const custom = normalizeLegacyCustom(customRaw);
    const recent = normalizeLegacyRecent(recentRaw);

    if (favorites.length === 0 && custom.length === 0 && recent.length === 0) {
      return {};
    }
    return { favorites, custom, recent };
  } catch {
    return {};
  }
}

const legacy = readLegacy();

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set) => ({
      favorites: legacy.favorites ?? [],
      custom: legacy.custom ?? [],
      recent: legacy.recent ?? [],
      serverIds: {},
      apiBase: import.meta.env.VITE_API_BASE_URL ?? "",
      apiKey: "",
      composer: { ...EMPTY_COMPOSER },
      view: "all",
      category: "All",
      searchTerm: "",
      server: { status: "unknown", info: null },

      setField: (key, value) =>
        set((state) => ({ composer: { ...state.composer, [key]: value } })),

      resetComposer: () =>
        set((state) => ({
          composer: { ...EMPTY_COMPOSER, region: state.composer.region },
        })),

      loadQuery: (query) =>
        set((state) => ({
          composer: {
            ...EMPTY_COMPOSER,
            region: state.composer.region,
            terms: query,
          },
        })),

      toggleFavorite: (id) =>
        set((state) => ({
          favorites: state.favorites.includes(id)
            ? state.favorites.filter((value) => value !== id)
            : [...state.favorites, id],
        })),

      addCustom: (preset) =>
        set((state) => ({ custom: [preset, ...state.custom] })),

      deleteCustom: (id) =>
        set((state) => {
          const serverIds = { ...state.serverIds };
          delete serverIds[id];
          return {
            custom: state.custom.filter((preset) => preset.id !== id),
            favorites: state.favorites.filter((value) => value !== id),
            serverIds,
          };
        }),

      attachServerId: (id, serverId) =>
        set((state) => ({
          serverIds: { ...state.serverIds, [id]: serverId },
          custom: state.custom.map((preset) =>
            preset.id === id ? { ...preset, serverId } : preset,
          ),
        })),

      recordRecent: (entry) =>
        set((state) => ({
          recent: [
            entry,
            ...state.recent.filter(
              (item) => !(item.query === entry.query && item.mode === entry.mode),
            ),
          ].slice(0, 12),
        })),

      setView: (view) => set({ view, category: "All" }),

      setCategory: (category) => set({ category, view: "all" }),

      setSearchTerm: (searchTerm) => set({ searchTerm }),

      setApiConfig: (apiBase, apiKey) => set({ apiBase, apiKey }),

      setServer: (server) => set({ server }),

      mergeServerPresets: (serverPresets) =>
        set((state) => {
          const favorites = new Set(state.favorites);
          const serverIds = { ...state.serverIds };
          const custom = state.custom.map((preset) => ({ ...preset }));
          const builtinIds = new Map(
            BUILTIN_PRESETS.map((preset) => [preset.title, preset.id]),
          );

          for (const preset of serverPresets) {
            if (preset.builtin) {
              const localId = builtinIds.get(preset.title);
              if (!localId) continue;
              serverIds[localId] = preset.id;
              if (preset.favorite) favorites.add(localId);
              else favorites.delete(localId);
              continue;
            }

            let local = custom.find((item) => item.serverId === preset.id);
            if (!local) {
              local = custom.find(
                (item) =>
                  item.title === preset.title && item.query === preset.query,
              );
            }

            if (local) {
              local.serverId = preset.id;
              serverIds[local.id] = preset.id;
            } else {
              const id = `c${preset.id}`;
              local = {
                id,
                serverId: preset.id,
                title: preset.title,
                description: preset.description,
                category: asCategory(preset.category),
                query: preset.query,
                scope: preset.scope === "Scoped" ? "Scoped" : "General",
                source: "custom",
              };
              custom.push(local);
              serverIds[id] = preset.id;
            }

            if (preset.favorite) favorites.add(local.id);
            else favorites.delete(local.id);
          }

          return { custom, serverIds, favorites: [...favorites] };
        }),
    }),
    {
      name: "dork-atlas-workspace-v1",
      version: 1,
      partialize: (state): Persisted => ({
        favorites: state.favorites,
        custom: state.custom,
        recent: state.recent,
        serverIds: state.serverIds,
        apiBase: state.apiBase,
        apiKey: state.apiKey,
      }),
    },
  ),
);
