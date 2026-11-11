import { Compass, Menu, Plus, Server } from "lucide-react";

import { Button } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/stores/workspace";

interface TopBarProps {
  onNewPreset: () => void;
  onOpenSettings: () => void;
  onOpenMenu: () => void;
}

export function TopBar({
  onNewPreset,
  onOpenSettings,
  onOpenMenu,
}: TopBarProps) {
  const status = useWorkspace((state) => state.server.status);
  const label =
    status === "online"
      ? "Atlas online"
      : status === "checking"
        ? "Checking Atlas"
        : "Local only";
  const dot =
    status === "online"
      ? "bg-accent"
      : status === "checking"
        ? "bg-fg-muted"
        : "bg-[#5b5b60]";

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-line bg-deep/90 backdrop-blur-md max-[560px]:h-14">
      <div className="mx-auto flex h-full max-w-content items-center justify-between gap-4 px-8 max-sm:px-4">
        <a
          href="#top"
          className="flex items-center gap-3"
          aria-label="Dork Atlas home"
        >
          <span className="grid h-9 w-9 place-items-center rounded-control border border-lineStrong bg-surface text-fg max-[560px]:h-8 max-[560px]:w-8">
            <Compass size={18} strokeWidth={1.5} />
          </span>
          <span className="block">
            <span className="block text-sm font-semibold leading-tight text-fg max-[560px]:text-[13px]">
              Dork Atlas
            </span>
            <span className="mt-0.5 block text-xs leading-tight text-fg-muted max-[560px]:hidden">
              Google search workbench
            </span>
          </span>
        </a>

        <div className="hidden items-center gap-6 text-xs text-fg-secondary md:flex">
          <span>Local-first workspace</span>
          <span className="border-l border-line pl-6">
            Sync only when you ask
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenSettings}
            className="hidden h-8 items-center gap-2 rounded-control border border-line bg-surface px-2.5 text-xs text-fg-secondary transition-colors duration-150 ease-out hover:border-lineStrong hover:text-fg sm:flex"
            aria-label={`Atlas server: ${label}`}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
            {label}
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            className="icon-btn relative sm:hidden"
            aria-label={`Atlas server: ${label}`}
            title={`Atlas server: ${label}`}
          >
            <Server size={16} strokeWidth={1.5} />
            <span
              className={cn(
                "absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full ring-2 ring-deep",
                dot,
              )}
              aria-hidden
            />
          </button>

          <Button variant="secondary" size="sm" onClick={onNewPreset}>
            <Plus size={16} strokeWidth={1.5} />
            <span className="max-[560px]:hidden">New preset</span>
          </Button>

          <button
            type="button"
            onClick={onOpenMenu}
            className="icon-btn lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={16} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </header>
  );
}
