import { useCallback, useState } from "react";

import { newId } from "@/lib/utils";
import { api } from "@/services/api";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";
import type { SearchResponse } from "@/types";

interface AtlasState {
  loading: boolean;
  error: string | null;
  response: SearchResponse | null;
  lastQuery: string;
}

const INITIAL: AtlasState = {
  loading: false,
  error: null,
  response: null,
  lastQuery: "",
};

export function useAtlasSearch() {
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const region = useWorkspace((state) => state.composer.region);
  const recordRecent = useWorkspace((state) => state.recordRecent);
  const showToast = useToast((state) => state.show);
  const [state, setState] = useState<AtlasState>(INITIAL);

  const run = useCallback(
    async (query: string, page = 1) => {
      const trimmed = query.trim();
      if (!trimmed) {
        showToast("Add a search term or load a preset first");
        return;
      }

      setState((previous) => ({
        ...previous,
        loading: true,
        error: null,
        lastQuery: trimmed,
      }));

      try {
        const response = await api.search(
          { baseUrl: apiBase, apiKey },
          {
            query: trimmed,
            page,
            region: region === "ZZ" ? "" : region,
          },
        );

        setState({
          loading: false,
          error: null,
          response,
          lastQuery: trimmed,
        });

        if (page === 1) {
          recordRecent({
            id: newId(),
            query: trimmed,
            label: "Atlas search",
            at: Date.now(),
            mode: "atlas",
            resultCount: response.total,
          });
        }
      } catch (error) {
        setState({
          loading: false,
          error:
            error instanceof Error ? error.message : "Atlas search failed",
          response: null,
          lastQuery: trimmed,
        });
      }
    },
    [apiBase, apiKey, recordRecent, region, showToast],
  );

  const reset = useCallback(() => setState(INITIAL), []);

  return { ...state, run, reset };
}
