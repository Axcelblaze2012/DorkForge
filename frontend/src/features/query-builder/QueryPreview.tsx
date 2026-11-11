import { Copy } from "lucide-react";

import { QueryText } from "@/components/ui/QueryText";
import { IconButton } from "@/components/ui/primitives";
import { cleanDomain, regionLabel, timeRangeLabel } from "@/lib/query";
import { cn, copyText } from "@/lib/utils";
import { useToast } from "@/stores/toast";
import type { ComposerFields, Diagnostic } from "@/types";

interface QueryPreviewProps {
  query: string;
  operators: string[];
  diagnostics: Diagnostic[];
  source: "local" | "atlas";
  fields: ComposerFields;
  online: boolean;
  className?: string;
}

export function QueryPreview({
  query,
  operators,
  diagnostics,
  source,
  fields,
  online,
  className,
}: QueryPreviewProps) {
  const showToast = useToast((state) => state.show);

  const handleCopy = async () => {
    if (!query) {
      showToast("Nothing to copy");
      return;
    }
    const copied = await copyText(query);
    showToast(copied ? "Query copied to clipboard" : "Could not copy the query");
  };

  const scope = cleanDomain(fields.domain) || "Any public site";
  const filetype = fields.filetype.trim();

  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-3 rounded-card border border-line bg-input p-4",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-xs text-fg-secondary">
          <span className="h-2 w-[2px] bg-accent" aria-hidden />
          Live query preview
        </span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] tabular-nums text-fg-muted">
            {operators.length}{" "}
            {operators.length === 1 ? "operator" : "operators"}
          </span>
          <IconButton
            label="Copy query"
            onClick={handleCopy}
            disabled={!query}
          >
            <Copy size={14} strokeWidth={1.5} />
          </IconButton>
        </div>
      </div>

      <QueryText
        query={query}
        placeholder="Your Google query will appear here"
        className="min-h-[72px] flex-1 whitespace-pre-wrap break-words text-[13px] leading-[1.7]"
      />

      {diagnostics.length > 0 ? (
        <ul className="space-y-1 border-t border-line pt-3">
          {diagnostics.slice(0, 3).map((diagnostic, index) => (
            <li
              key={`${diagnostic.code}-${index}`}
              className={cn(
                "flex gap-2 text-[11px] leading-relaxed",
                diagnostic.level === "error" ? "text-danger" : "text-fg-muted",
              )}
            >
              <span
                className="mt-1.5 h-1 w-1 flex-none rounded-full bg-current"
                aria-hidden
              />
              {diagnostic.message}
            </li>
          ))}
        </ul>
      ) : null}

      <dl className="mt-auto grid gap-1.5 border-t border-line pt-3 text-[11px]">
        <ContextRow
          label="Destination"
          value={online ? "Google + Atlas" : "Google"}
        />
        <ContextRow label="Region" value={regionLabel(fields.region)} />
        <ContextRow label="Scope" value={scope} mono />
        <ContextRow label="Window" value={timeRangeLabel(fields.timeRange)} />
        <ContextRow
          label="Format"
          value={filetype ? filetype.toUpperCase() : "Any format"}
        />
        <ContextRow
          label="Operators"
          value={operators.length > 0 ? operators.join(" · ") : "Plain terms"}
          mono
        />
      </dl>

      <div className="flex items-center justify-between gap-2 text-[11px] text-fg-muted">
        <span>
          {source === "atlas" ? "Rendered by Atlas" : "Rendered locally"}
        </span>
        {query ? (
          <span className="font-mono tabular-nums">{query.length}/900</span>
        ) : null}
      </div>
    </div>
  );
}

function ContextRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="flex-none text-fg-muted">{label}</dt>
      <dd
        className={cn(
          "truncate text-right text-fg-secondary",
          mono && "font-mono",
        )}
        title={value}
      >
        {value}
      </dd>
    </div>
  );
}
