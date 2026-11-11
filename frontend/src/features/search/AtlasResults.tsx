import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Loader2,
  TriangleAlert,
  X,
} from "lucide-react";

import { QueryText } from "@/components/ui/QueryText";
import { Button, IconButton, Tag } from "@/components/ui/primitives";
import { cn, formatNumber } from "@/lib/utils";
import type { ResultCard, SearchResponse } from "@/types";

interface AtlasResultsProps {
  response: SearchResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onPage: (page: number) => void;
  onRetry: () => void;
}

function domainOf(result: ResultCard): string {
  if (result.domain) return result.domain;
  try {
    return new URL(result.url).hostname;
  } catch {
    return result.url;
  }
}

export function AtlasResults({
  response,
  loading,
  error,
  onClose,
  onPage,
  onRetry,
}: AtlasResultsProps) {
  return (
    <section
      id="atlas-results"
      className="mb-10 animate-fade-up scroll-mt-24"
      aria-label="Atlas search results"
    >
      <div className="panel overflow-hidden">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-raised px-5 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="h-4 w-[2px] flex-none bg-accent" aria-hidden />
            <h2 className="text-[13px] font-medium text-fg">Atlas results</h2>
            {response ? (
              <span className="truncate font-mono text-[11px] tabular-nums text-fg-muted">
                {formatNumber(response.total)} results · {response.elapsed_ms} ms
                {response.cached ? " · cached" : ""}
              </span>
            ) : null}
          </div>
          <IconButton label="Close results" onClick={onClose}>
            <X size={16} strokeWidth={1.5} />
          </IconButton>
        </header>

        <div className="p-5">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} onRetry={onRetry} />
          ) : response ? (
            <Results response={response} onPage={onPage} />
          ) : null}
        </div>
      </div>
    </section>
  );
}

function Results({
  response,
  onPage,
}: {
  response: SearchResponse;
  onPage: (page: number) => void;
}) {
  return (
    <div>
      <div className="rounded-control border border-line bg-input px-3 py-2.5">
        <QueryText
          query={response.rendered_query}
          className="text-xs leading-relaxed [overflow-wrap:anywhere]"
        />
      </div>

      {response.warnings.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {response.warnings.map((warning, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs leading-relaxed text-fg-secondary"
            >
              <TriangleAlert
                size={14}
                strokeWidth={1.5}
                className="mt-0.5 flex-none text-fg-muted"
              />
              {warning}
            </li>
          ))}
        </ul>
      ) : null}

      {response.provider_statuses.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {response.provider_statuses.map((status) => (
            <span
              key={status.provider}
              className="inline-flex items-center gap-2 rounded-tag border border-line bg-raised px-2 py-1 text-[11px] text-fg-secondary"
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  status.status === "ok"
                    ? "bg-accent"
                    : status.status === "error"
                      ? "bg-danger"
                      : "bg-[#5b5b60]",
                )}
                aria-hidden
              />
              {status.provider}
              <span className="font-mono tabular-nums text-fg-muted">
                {status.count} · {status.latency_ms} ms
              </span>
            </span>
          ))}
        </div>
      ) : null}

      {response.results.length === 0 ? (
        <div className="mt-4 rounded-card border border-dashed border-lineStrong px-5 py-10 text-center text-[13px] text-fg-muted">
          <strong className="mb-1.5 block text-sm font-medium text-fg">
            No results returned
          </strong>
          {response.warnings[0] ??
            "Atlas returned an empty result set. Check the provider configuration in Settings."}
        </div>
      ) : (
        <ol className="mt-4 divide-y divide-line">
          {response.results.map((result, index) => (
            <li
              key={`${result.url}-${index}`}
              className="grid grid-cols-[28px_minmax(0,1fr)] gap-3 py-3.5 first:pt-1 last:pb-1"
            >
              <span className="pt-0.5 font-mono text-[11px] tabular-nums text-fg-muted">
                {String(
                  (response.page - 1) * response.per_page + index + 1,
                ).padStart(2, "0")}
              </span>

              <div className="min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex min-w-0 items-start gap-1.5 text-sm font-medium text-fg transition-colors duration-150 ease-out hover:text-accent"
                  >
                    <span className="truncate">{result.title}</span>
                    <ArrowUpRight
                      size={14}
                      strokeWidth={1.5}
                      className="mt-0.5 flex-none text-fg-muted group-hover:text-accent"
                    />
                  </a>
                  {result.provider ? <Tag>{result.provider}</Tag> : null}
                </div>

                <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-fg-muted">
                  <span className="truncate">{domainOf(result)}</span>
                  {result.published_date ? (
                    <span>· {result.published_date}</span>
                  ) : null}
                </div>

                {result.snippet ? (
                  <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-fg-secondary">
                    {result.snippet}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}

      {response.total_pages > 1 ? (
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-4">
          <span className="font-mono text-[11px] tabular-nums text-fg-muted">
            Page {response.page} of {response.total_pages}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onPage(response.page - 1)}
              disabled={response.page <= 1}
            >
              <ArrowLeft size={14} strokeWidth={1.5} />
              Previous
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onPage(response.page + 1)}
              disabled={response.page >= response.total_pages}
            >
              Next
              <ArrowRight size={14} strokeWidth={1.5} />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function LoadingState() {
  return (
    <div>
      <div className="flex items-center gap-2 text-[13px] text-fg-secondary">
        <Loader2 size={15} strokeWidth={1.5} className="animate-spin" />
        Searching Atlas
      </div>
      <div className="mt-4 space-y-4">
        {[0, 1, 2].map((row) => (
          <div key={row} className="space-y-2">
            <div className="h-3 w-2/5 rounded bg-raised" />
            <div className="h-2.5 w-1/4 rounded bg-raised" />
            <div className="h-2.5 w-4/5 rounded bg-raised" />
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex items-start gap-3">
      <TriangleAlert
        size={16}
        strokeWidth={1.5}
        className="mt-0.5 flex-none text-danger"
      />
      <div>
        <p className="text-[13px] font-medium text-fg">Atlas search failed</p>
        <p className="mt-1 text-xs leading-relaxed text-fg-muted">{message}</p>
        <p className="mt-1 text-xs leading-relaxed text-fg-muted">
          Check the server URL and provider configuration in Settings.
        </p>
        <Button
          size="sm"
          variant="secondary"
          className="mt-3"
          onClick={onRetry}
        >
          Try again
        </Button>
      </div>
    </div>
  );
}
