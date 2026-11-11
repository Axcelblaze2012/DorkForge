import { useCallback } from "react";

import { ApiError, api } from "@/services/api";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";
import type { Preset } from "@/types";
import { copyText } from "@/lib/utils";

export function usePresetActions() {
  const toggleFavorite = useWorkspace((state) => state.toggleFavorite);
  const deleteCustom = useWorkspace((state) => state.deleteCustom);
  const loadQuery = useWorkspace((state) => state.loadQuery);
  const serverIds = useWorkspace((state) => state.serverIds);
  const favorites = useWorkspace((state) => state.favorites);
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const online = useWorkspace((state) => state.server.status === "online");
  const showToast = useToast((state) => state.show);

  const favorite = useCallback(
    async (preset: Preset) => {
      const nextFavorite = !favorites.includes(preset.id);
      toggleFavorite(preset.id);

      const serverId = preset.serverId ?? serverIds[preset.id];
      if (!online || !serverId) return;

      try {
        await api.setFavorite(
          { baseUrl: apiBase, apiKey },
          serverId,
          nextFavorite,
        );
      } catch {
        toggleFavorite(preset.id);
        showToast("Atlas did not save that favorite");
      }
    },
    [
      apiBase,
      apiKey,
      favorites,
      online,
      serverIds,
      showToast,
      toggleFavorite,
    ],
  );

  const remove = useCallback(
    async (preset: Preset) => {
      const serverId = preset.serverId ?? serverIds[preset.id];

      if (!online && serverId) {
        deleteCustom(preset.id);
        showToast("Removed locally; the Atlas copy remains");
        return;
      }

      if (online && serverId) {
        try {
          await api.deletePreset({ baseUrl: apiBase, apiKey }, serverId);
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 404)) {
            showToast("Atlas could not delete that preset");
            return;
          }
        }
      }

      deleteCustom(preset.id);
      showToast("Preset deleted");
    },
    [apiBase, apiKey, deleteCustom, online, serverIds, showToast],
  );

  const copy = useCallback(
    async (resolvedQuery: string) => {
      const copied = await copyText(resolvedQuery);
      showToast(copied ? "Query copied to clipboard" : "Could not copy the query");
    },
    [showToast],
  );

  const use = useCallback(
    (resolvedQuery: string) => {
      loadQuery(resolvedQuery);
      window.scrollTo({ top: 0, behavior: "smooth" });
      window.requestAnimationFrame(() => {
        document.getElementById("composer-terms")?.focus();
      });
      showToast("Preset loaded into the composer");
    },
    [loadQuery, showToast],
  );

  return { favorite, remove, copy, use };
}
