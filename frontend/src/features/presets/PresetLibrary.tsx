import { useMemo } from "react";

import { Button, Keycap } from "@/components/ui/primitives";
import { BUILTIN_PRESETS } from "@/data/builtins";
import { RecentSearches } from "@/features/history/RecentSearches";
import { cleanDomain, resolveTemplate } from "@/lib/query";
import { cn, copyText } from "@/lib/utils";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";
import { CATEGORIES } from "@/types";
import { PresetCard } from "./PresetCard";
import { usePresetActions } from "./usePresetActions";

const VIEW_COPY = {
  all: {
    title: "Preset library",
    subtitle: "Curated patterns for precise public-web research",
  },
  favorites: {
    title: "Favorites",
    subtitle: "Your bookmarked search patterns",
  },
  custom: {
    title: "My presets",
    subtitle: "Your locally saved search patterns",
  },
  recent: {
    title: "Recent searches",
    subtitle: "Queries you launched from this workspace",
  },
} as const;

export function PresetLibrary() {
  const view = useWorkspace((state) => state.view);
  const category = useWorkspace((state) => state.category);
  const searchTerm = useWorkspace((state) => state.searchTerm);
  const favorites = useWorkspace((state) => state.favorites);
  const custom = useWorkspace((state) => state.custom);
  const recent = useWorkspace((state) => state.recent);
  const composer = useWorkspace((state) => state.composer);
  const setSearchTerm = useWorkspace((state) => state.setSearchTerm);
  const setCategory = useWorkspace((state) => state.setCategory);
  const setView = useWorkspace((state) => state.setView);
  const loadQuery = useWorkspace((state) => state.loadQuery);
  const showToast = useToast((state) => state.show);
  const actions = usePresetActions();

  const term = searchTerm.trim().toLowerCase();
  const domain = cleanDomain(composer.domain);
  const topic = composer.terms.trim();

  const allPresets = useMemo(
    () => [...BUILTIN_PRESETS, ...custom],
    [custom],
  );

  const items = useMemo(() => {
    let list = allPresets;

    if (view === "favorites") {
      list = list.filter((preset) => favorites.includes(preset.id));
    } else if (view === "custom") {
      list = list.filter((preset) => preset.source === "custom");
    }

    if (category !== "All") {
      list = list.filter((preset) => preset.category === category);
    }

    if (term) {
      list = list.filter((preset) =>
        `${preset.title} ${preset.description} ${preset.category} ${preset.query}`
          .toLowerCase()
          .includes(term),
      );
    }

    return list;
  }, [allPresets, category, favorites, term, view]);

  const recentItems = useMemo(
    () =>
      recent.filter((item) => !term || item.query.toLowerCase().includes(term)),
    [recent, term],
  );

  const copy = (query: string) => {
    void copyText(query).then((copied) => {
      showToast(
        copied ? "Query copied to clipboard" : "Could not copy the query",
      );
    });
  };

  const clearFilters = () => {
    setSearchTerm("");
    setCategory("All");
    setView("all");
  };

  const copyLabel = VIEW_COPY[view];

  return (
    <section aria-label="Dork library">
      <div className="mb-5 flex items-end justify-between gap-5 max-sm:flex-col max-sm:items-stretch">
        <div>
          <h2 className="text-xl font-medium leading-tight text-fg">
            {copyLabel.title}
          </h2>
          <p className="mt-1 text-[13px] text-fg-muted">{copyLabel.subtitle}</p>
        </div>

        <div className="flex items-center gap-2 max-sm:w-full">
          <div className="relative">
            <input
              id="catalog-search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Find a preset"
              aria-label="Find a preset"
              className="field h-9 w-[240px] pr-9 max-sm:w-full"
            />
            <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2">
              <Keycap>/</Keycap>
            </span>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={clearFilters}
            className="flex-none"
          >
            Clear filters
          </Button>
        </div>
      </div>

      {view !== "recent" ? (
        <div className="mb-3 flex gap-2 overflow-x-auto pb-3">
          {["All", ...CATEGORIES].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={cn("pill", category === item && "pill-active")}
              aria-pressed={category === item}
            >
              {item}
            </button>
          ))}
        </div>
      ) : null}

      <div className="mb-4 flex items-center justify-between gap-3 text-xs text-fg-muted">
        <span>
          {view === "recent" ? (
            <>
              Showing{" "}
              <strong className="font-mono font-medium tabular-nums text-fg">
                {recentItems.length}
              </strong>{" "}
              recent searches
            </>
          ) : (
            <>
              Showing{" "}
              <strong className="font-mono font-medium tabular-nums text-fg">
                {items.length}
              </strong>{" "}
              {items.length === 1 ? "preset" : "presets"}
            </>
          )}
        </span>
        <span className="max-sm:hidden">
          {view === "recent"
            ? "Load a query to reuse it"
            : "Select a preset to load it into the composer"}
        </span>
      </div>

      {view === "recent" ? (
        <RecentSearches
          items={recentItems}
          onCopy={copy}
          onUse={(query) => {
            loadQuery(query);
            window.scrollTo({ top: 0, behavior: "smooth" });
            window.requestAnimationFrame(() => {
              document.getElementById("composer-terms")?.focus();
            });
            showToast("Recent query loaded");
          }}
        />
      ) : items.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {items.map((preset) => {
            const resolvedQuery = resolveTemplate(preset.query, domain, topic);
            return (
              <PresetCard
                key={preset.id}
                preset={preset}
                resolvedQuery={resolvedQuery}
                favorite={favorites.includes(preset.id)}
                onFavorite={() => void actions.favorite(preset)}
                onCopy={() => void actions.copy(resolvedQuery)}
                onUse={() => actions.use(resolvedQuery)}
                onDelete={() => void actions.remove(preset)}
              />
            );
          })}
        </div>
      ) : (
        <div className="empty-state">
          <strong className="mb-1.5 block text-sm font-medium text-fg">
            {view === "favorites"
              ? "No favorites yet"
              : view === "custom"
                ? "No custom presets yet"
                : "Nothing matches this filter"}
          </strong>
          {view === "favorites"
            ? "Star a preset to keep it here"
            : view === "custom"
              ? "Create one with New preset"
              : "Try another category or clear the search"}
        </div>
      )}
    </section>
  );
}
