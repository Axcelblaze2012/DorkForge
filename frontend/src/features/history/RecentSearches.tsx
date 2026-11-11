import { ArrowUpRight, Copy } from "lucide-react";

import { Button, IconButton } from "@/components/ui/primitives";
import { formatNumber, formatWhen } from "@/lib/utils";
import type { RecentSearch } from "@/types";

interface RecentSearchesProps {
  items: RecentSearch[];
  onCopy: (query: string) => void;
  onUse: (query: string) => void;
}

export function RecentSearches({ items, onCopy, onUse }: RecentSearchesProps) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong className="mb-1.5 block text-sm font-medium text-fg">
          No recent searches yet
        </strong>
        Queries you launch will appear here
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {items.map((item) => (
        <article key={item.id} className="dork-card">
          <div className="mb-2 flex items-start justify-between gap-3">
            <h3 className="text-sm font-medium leading-snug text-fg">
              {item.mode === "atlas" ? "Atlas search" : "Google search"}
            </h3>
            <span className="font-mono text-[11px] text-fg-muted">
              {formatWhen(item.at)}
            </span>
          </div>

          <div className="card-query" title={item.query}>
            {item.query}
          </div>

          <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
            <span className="font-mono text-[11px] text-fg-muted">
              {item.resultCount != null
                ? `${formatNumber(item.resultCount)} results`
                : "Opened on Google"}
            </span>
            <div className="flex items-center gap-1.5">
              <IconButton
                label="Copy query"
                onClick={() => onCopy(item.query)}
              >
                <Copy size={14} strokeWidth={1.5} />
              </IconButton>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onUse(item.query)}
              >
                Load query
                <ArrowUpRight size={14} strokeWidth={1.5} />
              </Button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
