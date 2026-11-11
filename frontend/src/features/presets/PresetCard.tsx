import { ArrowUpRight, Copy, Star, Trash2 } from "lucide-react";

import { Button, IconButton, Tag } from "@/components/ui/primitives";
import type { Preset } from "@/types";

interface PresetCardProps {
  preset: Preset;
  resolvedQuery: string;
  favorite: boolean;
  onFavorite: () => void;
  onCopy: () => void;
  onUse: () => void;
  onDelete: () => void;
}

export function PresetCard({
  preset,
  resolvedQuery,
  favorite,
  onFavorite,
  onCopy,
  onUse,
  onDelete,
}: PresetCardProps) {
  return (
    <article className="dork-card">
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="text-sm font-medium leading-snug text-fg">
          {preset.title}
        </h3>
        <IconButton
          label={favorite ? "Remove favorite" : "Add favorite"}
          active={favorite}
          onClick={onFavorite}
        >
          <Star
            size={15}
            strokeWidth={1.5}
            fill={favorite ? "currentColor" : "none"}
          />
        </IconButton>
      </div>

      <p className="mb-3 min-h-[38px] text-[13px] leading-relaxed text-fg-secondary">
        {preset.description}
      </p>

      <div className="flex flex-wrap items-center gap-1.5">
        <Tag>{preset.category}</Tag>
        <Tag tone="secondary">
          {preset.scope === "Scoped" ? "Domain scoped" : "General research"}
        </Tag>
      </div>

      <div className="card-query" title={resolvedQuery}>
        {resolvedQuery}
      </div>

      <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
        <span className="font-mono text-[11px] text-fg-muted">
          {preset.source === "builtin" ? "Atlas library" : "Your preset"}
        </span>
        <div className="flex items-center gap-1.5">
          {preset.source === "custom" ? (
            <IconButton label="Delete preset" onClick={onDelete}>
              <Trash2 size={14} strokeWidth={1.5} />
            </IconButton>
          ) : null}
          <IconButton label="Copy query" onClick={onCopy}>
            <Copy size={14} strokeWidth={1.5} />
          </IconButton>
          <Button size="sm" variant="secondary" onClick={onUse}>
            Use preset
            <ArrowUpRight size={14} strokeWidth={1.5} />
          </Button>
        </div>
      </div>
    </article>
  );
}
