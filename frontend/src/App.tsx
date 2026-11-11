import { useEffect, useState } from "react";

import { BottomNote } from "@/components/layout/BottomNote";
import { PageHeader } from "@/components/layout/PageHeader";
import { MobileSidebar, Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Toast } from "@/components/ui/Toast";
import { PresetLibrary } from "@/features/presets/PresetLibrary";
import { PresetModal } from "@/features/presets/PresetModal";
import { QueryComposer } from "@/features/query-builder/QueryComposer";
import { AtlasResults } from "@/features/search/AtlasResults";
import { SettingsModal } from "@/features/settings/SettingsModal";
import { useAtlasSearch } from "@/hooks/useAtlasSearch";
import { useHotkeys } from "@/hooks/useHotkeys";
import { useServerProbe } from "@/hooks/useServerProbe";

export default function App() {
  useServerProbe();
  useHotkeys();

  const atlas = useAtlasSearch();
  const [presetOpen, setPresetOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!atlas.loading) return;
    document
      .getElementById("atlas-results")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [atlas.loading]);

  return (
    <div className="min-h-screen bg-deep">
      <TopBar
        onNewPreset={() => setPresetOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenMenu={() => setMobileOpen(true)}
      />

      <div
        id="top"
        className="mx-auto grid w-full max-w-content grid-cols-1 gap-10 px-8 pb-16 pt-8 max-sm:px-4 max-sm:pt-6 lg:grid-cols-[256px_minmax(0,1fr)]"
      >
        <Sidebar />

        <main className="min-w-0">
          <PageHeader />

          <QueryComposer
            onRunAtlas={(query) => void atlas.run(query)}
            atlasLoading={atlas.loading}
          />

          {atlas.loading || atlas.response || atlas.error ? (
            <AtlasResults
              response={atlas.response}
              loading={atlas.loading}
              error={atlas.error}
              onClose={atlas.reset}
              onPage={(page) => void atlas.run(atlas.lastQuery, page)}
              onRetry={() => void atlas.run(atlas.lastQuery)}
            />
          ) : null}

          <PresetLibrary />
          <BottomNote />
        </main>
      </div>

      <MobileSidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />
      <PresetModal open={presetOpen} onClose={() => setPresetOpen(false)} />
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <Toast />
    </div>
  );
}
