import { useEffect } from "react";
import {
  History,
  LayoutGrid,
  ListPlus,
  Star,
  X,
  type LucideIcon,
} from "lucide-react";

import { IconButton } from "@/components/ui/primitives";
import { BUILTIN_PRESETS } from "@/data/builtins";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/stores/workspace";
import { CATEGORIES, type View } from "@/types";

const VIEWS: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "all", label: "All dorks", icon: LayoutGrid },
  { id: "favorites", label: "Favorites", icon: Star },
  { id: "custom", label: "My presets", icon: ListPlus },
  { id: "recent", label: "Recent searches", icon: History },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const view = useWorkspace((state) => state.view);
  const category = useWorkspace((state) => state.category);
  const favorites = useWorkspace((state) => state.favorites);
  const custom = useWorkspace((state) => state.custom);
  const recent = useWorkspace((state) => state.recent);
  const setView = useWorkspace((state) => state.setView);
  const setCategory = useWorkspace((state) => state.setCategory);

  const allPresets = [...BUILTIN_PRESETS, ...custom];
  const counts: Record<View, number> = {
    all: allPresets.length,
    favorites: favorites.length,
    custom: custom.length,
    recent: recent.length,
  };

  return (
    <div>
      <div className="side-label mb-2 mt-1 text-xs text-fg-muted">Workspace</div>
      <nav className="grid gap-1" aria-label="Workspace">
        {VIEWS.map((item) => {
          const Icon = item.icon;
          const active = view === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setView(item.id);
                onNavigate?.();
              }}
              className={cn("nav-item", active && "nav-item-active")}
              aria-current={active ? "page" : undefined}
            >
              {active ? (
                <span
                  className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 bg-accent"
                  aria-hidden
                />
              ) : null}
              <Icon
                size={16}
                strokeWidth={1.5}
                className={active ? "text-accent" : "text-fg-muted"}
              />
              {item.label}
              <span className="ml-auto font-mono text-xs tabular-nums text-fg-muted">
                {counts[item.id]}
              </span>
            </button>
          );
        })}
      </nav>

      <div className="side-label mb-2 mt-6 text-xs text-fg-muted">
        Browse categories
      </div>
      <div className="grid gap-0.5">
        {CATEGORIES.map((item) => {
          const count = allPresets.filter(
            (preset) => preset.category === item,
          ).length;
          const active = category === item;
          return (
            <button
              key={item}
              type="button"
              onClick={() => {
                setCategory(item);
                onNavigate?.();
              }}
              className={cn("cat-item", active && "cat-item-active")}
              aria-pressed={active}
            >
              <span>{item}</span>
              <span className="font-mono text-xs tabular-nums text-fg-muted">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-8 rounded-card border border-line bg-surface p-4">
        <div className="mb-1.5 text-xs font-medium text-fg">Use with intent</div>
        <p className="text-xs leading-relaxed text-fg-muted">
          Search public information only. Scope testing to assets you own or
          have explicit permission to assess.
        </p>
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden self-start lg:sticky lg:top-[88px] lg:block lg:max-h-[calc(100vh-104px)] lg:overflow-y-auto lg:pb-6 lg:pr-1">
      <SidebarContent />
    </aside>
  );
}

export function MobileSidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        aria-label="Close navigation"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        className="absolute inset-y-0 left-0 w-[280px] animate-fade-up overflow-y-auto border-r border-line bg-deep p-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm font-semibold text-fg">Dork Atlas</span>
          <IconButton label="Close navigation" onClick={onClose}>
            <X size={16} strokeWidth={1.5} />
          </IconButton>
        </div>
        <SidebarContent onNavigate={onClose} />
      </aside>
    </div>
  );
}
