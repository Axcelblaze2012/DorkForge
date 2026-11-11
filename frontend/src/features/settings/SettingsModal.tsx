import { useEffect, useState } from "react";
import { Download, Loader2, RefreshCw, Upload } from "lucide-react";

import { Modal } from "@/components/ui/Modal";
import { Button, Field, Input } from "@/components/ui/primitives";
import { cn, downloadJson } from "@/lib/utils";
import { api, probeServer } from "@/services/api";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";

type Busy = "import" | "push" | null;

export function SettingsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const server = useWorkspace((state) => state.server);
  const custom = useWorkspace((state) => state.custom);
  const favorites = useWorkspace((state) => state.favorites);
  const serverIds = useWorkspace((state) => state.serverIds);
  const setApiConfig = useWorkspace((state) => state.setApiConfig);
  const setServer = useWorkspace((state) => state.setServer);
  const attachServerId = useWorkspace((state) => state.attachServerId);
  const mergeServerPresets = useWorkspace(
    (state) => state.mergeServerPresets,
  );
  const showToast = useToast((state) => state.show);

  const [draftBase, setDraftBase] = useState(apiBase);
  const [draftKey, setDraftKey] = useState(apiKey);
  const [testing, setTesting] = useState(false);
  const [busy, setBusy] = useState<Busy>(null);

  useEffect(() => {
    if (!open) return;
    setDraftBase(apiBase);
    setDraftKey(apiKey);
  }, [apiBase, apiKey, open]);

  const online = server.status === "online";
  const statusLabel = online
    ? `Online${server.info?.version ? ` · v${server.info.version}` : ""}`
    : server.status === "checking"
      ? "Checking…"
      : "Offline";
  const dot = online
    ? "bg-accent"
    : server.status === "checking"
      ? "bg-fg-muted"
      : "bg-[#5b5b60]";

  const testConnection = async () => {
    setTesting(true);
    const info = await probeServer({ baseUrl: draftBase, apiKey: draftKey });
    setApiConfig(draftBase.trim(), draftKey);
    setServer(info ? { status: "online", info } : { status: "offline", info: null });
    setTesting(false);
    showToast(info ? `Connected to ${info.app}` : "No Atlas server answered");
  };

  const save = () => {
    setApiConfig(draftBase.trim(), draftKey);
    onClose();
  };

  const importFromAtlas = async () => {
    if (!online) {
      showToast("Connect to Atlas first");
      return;
    }

    setBusy("import");
    try {
      const result = await api.listPresets({ baseUrl: apiBase, apiKey });
      mergeServerPresets(result);
      showToast(`Synced ${result.length} presets from Atlas`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Import failed");
    } finally {
      setBusy(null);
    }
  };

  const pushToAtlas = async () => {
    if (!online) {
      showToast("Connect to Atlas first");
      return;
    }

    const pending = custom.filter(
      (preset) => !preset.serverId && !serverIds[preset.id],
    );
    if (pending.length === 0) {
      showToast("Every local preset is already on Atlas");
      return;
    }

    setBusy("push");
    let pushed = 0;
    let failed = 0;

    for (const preset of pending) {
      try {
        const created = await api.createPreset(
          { baseUrl: apiBase, apiKey },
          {
            title: preset.title,
            description: preset.description,
            query: preset.query,
            category: preset.category,
          },
        );
        attachServerId(preset.id, created.id);
        pushed += 1;
      } catch {
        failed += 1;
      }
    }

    setBusy(null);
    showToast(
      `${pushed} pushed${failed > 0 ? `, ${failed} failed` : ""}`,
    );
  };

  const exportPresets = () => {
    downloadJson(
      `dork-atlas-presets-${new Date().toISOString().slice(0, 10)}.json`,
      {
        format: "dork-atlas-presets-v1",
        exported_at: new Date().toISOString(),
        presets: custom.map((preset) => ({
          title: preset.title,
          description: preset.description,
          query: preset.query,
          category: preset.category,
          scope: preset.scope,
          tags: preset.tags ?? [],
          source: "custom",
          favorite: favorites.includes(preset.id),
        })),
      },
    );
    showToast("Preset export downloaded");
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Workspace settings"
      description="Optional Atlas connection, preset sync, and local data"
      width="max-w-[560px]"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={save}>
            Save changes
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <section>
          <h3 className="text-[13px] font-medium text-fg">Atlas server</h3>
          <p className="mt-1 text-xs leading-relaxed text-fg-muted">
            Without a server the workbench stays local. Search and sync only run
            when you choose them.
          </p>

          <div className="mt-3 grid gap-3">
            <Field
              label="Server URL"
              htmlFor="settings-base"
              hint="Leave empty to use the same origin."
            >
              <Input
                id="settings-base"
                value={draftBase}
                onChange={(event) => setDraftBase(event.target.value)}
                placeholder="http://127.0.0.1:8000"
                autoComplete="off"
                spellCheck={false}
              />
            </Field>

            <Field
              label="API key"
              htmlFor="settings-key"
              hint="Stored in this browser. Sent as X-API-Key."
            >
              <Input
                id="settings-key"
                type="password"
                value={draftKey}
                onChange={(event) => setDraftKey(event.target.value)}
                placeholder="Optional"
                autoComplete="off"
              />
            </Field>

            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-xs text-fg-secondary">
                <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
                {statusLabel}
              </span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void testConnection()}
                disabled={testing}
              >
                {testing ? (
                  <Loader2
                    size={14}
                    strokeWidth={1.5}
                    className="animate-spin"
                  />
                ) : (
                  <RefreshCw size={14} strokeWidth={1.5} />
                )}
                Test connection
              </Button>
            </div>
          </div>
        </section>

        <section className="border-t border-line pt-5">
          <h3 className="text-[13px] font-medium text-fg">Preset sync</h3>
          <p className="mt-1 text-xs leading-relaxed text-fg-muted">
            Pull server presets into this workspace, or push local custom
            presets to Atlas.
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void importFromAtlas()}
              disabled={!online || busy !== null}
            >
              {busy === "import" ? (
                <Loader2
                  size={14}
                  strokeWidth={1.5}
                  className="animate-spin"
                />
              ) : (
                <Download size={14} strokeWidth={1.5} />
              )}
              Import from Atlas
            </Button>

            <Button
              size="sm"
              variant="secondary"
              onClick={() => void pushToAtlas()}
              disabled={!online || busy !== null}
            >
              {busy === "push" ? (
                <Loader2
                  size={14}
                  strokeWidth={1.5}
                  className="animate-spin"
                />
              ) : (
                <Upload size={14} strokeWidth={1.5} />
              )}
              Push local presets
            </Button>
          </div>

          <p className="mt-2 text-[11px] leading-relaxed text-fg-muted">
            Import also brings server favorites. Push skips presets that already
            have a server id.
          </p>
        </section>

        <section className="border-t border-line pt-5">
          <h3 className="text-[13px] font-medium text-fg">Workspace data</h3>
          <p className="mt-1 text-xs leading-relaxed text-fg-muted">
            Custom presets only. Favorites travel as a flag.
          </p>
          <div className="mt-3">
            <Button size="sm" variant="secondary" onClick={exportPresets}>
              <Download size={14} strokeWidth={1.5} />
              Export presets
            </Button>
          </div>
        </section>
      </div>
    </Modal>
  );
}
