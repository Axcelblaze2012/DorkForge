import { useEffect } from "react";

import { probeServer } from "@/services/api";
import { useWorkspace } from "@/stores/workspace";

export function useServerProbe(): void {
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const setServer = useWorkspace((state) => state.setServer);

  useEffect(() => {
    let active = true;
    setServer({ status: "checking", info: null });

    const timer = window.setTimeout(async () => {
      const info = await probeServer({ baseUrl: apiBase, apiKey });
      if (!active) return;
      setServer(
        info
          ? { status: "online", info }
          : { status: "offline", info: null },
      );
    }, 120);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [apiBase, apiKey, setServer]);
}
