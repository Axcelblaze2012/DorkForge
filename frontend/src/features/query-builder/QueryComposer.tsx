import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Search, Server } from "lucide-react";

import {
  Button,
  Field,
  Input,
  Keycap,
  Select,
} from "@/components/ui/primitives";
import { api } from "@/services/api";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";
import {
  buildQuery,
  googleSearchUrl,
  localOperators,
  REGION_OPTIONS,
  TIME_RANGE_OPTIONS,
} from "@/lib/query";
import { newId } from "@/lib/utils";
import type { QueryPreview as QueryPreviewData } from "@/types";
import { OperatorChips } from "./OperatorChips";
import { QueryPreview } from "./QueryPreview";

const FILE_TYPES = [
  "pdf",
  "doc",
  "docx",
  "ppt",
  "pptx",
  "xls",
  "xlsx",
  "csv",
  "txt",
  "rtf",
  "odt",
  "odp",
  "ods",
  "xml",
  "json",
];

interface QueryComposerProps {
  onRunAtlas: (query: string) => void;
  atlasLoading: boolean;
}

export function QueryComposer({
  onRunAtlas,
  atlasLoading,
}: QueryComposerProps) {
  const fields = useWorkspace((state) => state.composer);
  const setField = useWorkspace((state) => state.setField);
  const resetComposer = useWorkspace((state) => state.resetComposer);
  const recordRecent = useWorkspace((state) => state.recordRecent);
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const serverStatus = useWorkspace((state) => state.server.status);
  const showToast = useToast((state) => state.show);

  const termsRef = useRef<HTMLInputElement>(null);
  const [serverPreview, setServerPreview] = useState<QueryPreviewData | null>(
    null,
  );

  const localQuery = useMemo(() => buildQuery(fields), [fields]);
  const localPreview = useMemo<QueryPreviewData>(
    () => ({
      query: localQuery,
      operators: localOperators(fields),
      diagnostics: [],
    }),
    [fields, localQuery],
  );

  useEffect(() => {
    if (serverStatus !== "online" || !localQuery) {
      setServerPreview(null);
      return;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const result = await api.previewQuery(
          { baseUrl: apiBase, apiKey },
          fields,
        );
        if (!active) return;
        setServerPreview({
          query: result.query,
          operators: result.operators,
          diagnostics: result.diagnostics,
        });
      } catch {
        if (active) setServerPreview(null);
      }
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [apiBase, apiKey, fields, localQuery, serverStatus]);

  const matchedServerPreview =
    serverPreview && serverPreview.query === localQuery ? serverPreview : null;
  const preview = matchedServerPreview ?? localPreview;
  const previewSource = matchedServerPreview ? "atlas" : "local";

  const insertOperator = (operator: string) => {
    const input = termsRef.current;
    const start = input?.selectionStart ?? fields.terms.length;
    const end = input?.selectionEnd ?? fields.terms.length;
    const next =
      fields.terms.slice(0, start) + operator + fields.terms.slice(end);
    setField("terms", next);

    window.requestAnimationFrame(() => {
      if (!input) return;
      input.focus();
      const position = start + operator.length;
      input.setSelectionRange(position, position);
    });
  };

  const launchGoogle = () => {
    const query = preview.query.trim();
    if (!query) {
      showToast("Add a search term or load a preset first");
      termsRef.current?.focus();
      return;
    }

    recordRecent({
      id: newId(),
      query,
      label: "Google search",
      at: Date.now(),
      mode: "google",
    });

    window.open(
      googleSearchUrl(query, fields.region),
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleAtlas = () => {
    const query = preview.query.trim();
    if (!query) {
      showToast("Add a search term or load a preset first");
      termsRef.current?.focus();
      return;
    }
    onRunAtlas(query);
  };

  const reset = () => {
    resetComposer();
    window.requestAnimationFrame(() => termsRef.current?.focus());
  };

  return (
    <section className="panel mb-10 overflow-hidden" aria-label="Google query builder">
      <div className="flex h-12 items-center justify-between gap-4 border-b border-line bg-raised px-5">
        <div className="flex items-center gap-2 text-[13px] font-medium text-fg">
          <span className="font-mono text-xs text-accent">01</span>
          Query composer
        </div>
        <span className="text-xs text-fg-muted max-sm:hidden">
          Build a search, then inspect it
        </span>
      </div>

      <div className="composer-grid p-6 max-sm:p-4">
        <div className="composer-area-label mb-2 flex justify-between gap-3 text-xs text-fg-secondary">
          <label htmlFor="composer-terms">Search terms</label>
          <span className="text-fg-muted">Press Enter to launch</span>
        </div>

        <div className="composer-area-input relative flex items-center">
          <Search
            size={16}
            strokeWidth={1.5}
            className="pointer-events-none absolute left-3.5 text-fg-muted"
          />
          <input
            id="composer-terms"
            ref={termsRef}
            value={fields.terms}
            onChange={(event) => setField("terms", event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                launchGoogle();
              }
            }}
            placeholder="e.g. annual report OR sustainability overview"
            autoComplete="off"
            spellCheck={false}
            className="field h-12 pl-10 pr-12 font-mono"
          />
          <span className="pointer-events-none absolute right-3">
            <Keycap>↵</Keycap>
          </span>
        </div>

        <div className="composer-area-preview mt-4 lg:mt-0">
          <QueryPreview
            query={preview.query}
            operators={preview.operators}
            diagnostics={preview.diagnostics}
            source={previewSource}
            fields={fields}
            online={serverStatus === "online"}
            className="h-full"
          />
        </div>

        <div className="composer-area-filters mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Field label="Target domain" htmlFor="composer-domain">
            <Input
              id="composer-domain"
              value={fields.domain}
              onChange={(event) => setField("domain", event.target.value)}
              placeholder="example.com"
              autoComplete="off"
              spellCheck={false}
            />
          </Field>

          <Field label="File type" htmlFor="composer-filetype">
            <Select
              id="composer-filetype"
              value={fields.filetype}
              onChange={(event) => setField("filetype", event.target.value)}
            >
              <option value="">Any format</option>
              {FILE_TYPES.map((filetype) => (
                <option key={filetype} value={filetype}>
                  {filetype}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="In page title" htmlFor="composer-title">
            <Input
              id="composer-title"
              value={fields.titleTerm}
              onChange={(event) => setField("titleTerm", event.target.value)}
              placeholder="title keyword"
            />
          </Field>

          <Field label="In URL" htmlFor="composer-url">
            <Input
              id="composer-url"
              value={fields.urlTerm}
              onChange={(event) => setField("urlTerm", event.target.value)}
              placeholder="path or keyword"
            />
          </Field>

          <Field label="Exact phrase" htmlFor="composer-exact">
            <Input
              id="composer-exact"
              value={fields.exactPhrase}
              onChange={(event) => setField("exactPhrase", event.target.value)}
              placeholder="words in quotes"
            />
          </Field>

          <Field label="Exclude term" htmlFor="composer-exclude">
            <Input
              id="composer-exclude"
              value={fields.excludeTerm}
              onChange={(event) => setField("excludeTerm", event.target.value)}
              placeholder="remove a word"
            />
          </Field>

          <Field label="Published / indexed" htmlFor="composer-time">
            <Select
              id="composer-time"
              value={fields.timeRange}
              onChange={(event) => setField("timeRange", event.target.value)}
            >
              {TIME_RANGE_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Google region" htmlFor="composer-region">
            <Select
              id="composer-region"
              value={fields.region}
              onChange={(event) => setField("region", event.target.value)}
            >
              {REGION_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="composer-area-operators">
          <OperatorChips onInsert={insertOperator} />
        </div>

        <div className="composer-area-actions mt-5 flex items-center justify-between gap-4 border-t border-line pt-4 max-sm:flex-col max-sm:items-stretch">
          <span className="max-w-[500px] text-xs leading-relaxed text-fg-muted">
            Google search opens in a new tab. Atlas search runs on your server
            only when you choose it.
          </span>
          <div className="flex flex-none gap-2 max-sm:w-full max-sm:flex-col">
            <Button variant="secondary" onClick={reset}>
              Reset
            </Button>
            <Button variant="primary" onClick={launchGoogle}>
              <Search size={16} strokeWidth={1.5} />
              <span>Search Google</span>
            </Button>
            {serverStatus === "online" ? (
              <Button
                variant="secondary"
                onClick={handleAtlas}
                disabled={atlasLoading}
              >
                {atlasLoading ? (
                  <Loader2
                    size={16}
                    strokeWidth={1.5}
                    className="animate-spin"
                  />
                ) : (
                  <Server size={16} strokeWidth={1.5} />
                )}
                <span>{atlasLoading ? "Running" : "Run on Atlas"}</span>
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
